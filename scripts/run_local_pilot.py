"""One pre-registered local inference, durable queue result, then Exometric seal."""
import argparse
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from modules.autoresearch.llm_client import LocalLLMClient
from modules.corpus.queue import CorpusQueue
from modules.corpus.witness import find_occurrences
from modules.audit.exometric import PINS, checked_copy, write_json, sha, seal_prepared_bundle

MODEL='qwen3.5:27b'
DIGEST='7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e'
OPTIONS={'num_ctx':8192,'num_predict':512,'temperature':0.2,'top_p':0.9,'seed':7}
BASE='http://localhost:11434'


def get(endpoint):
    r=requests.get(BASE+'/api/'+endpoint,timeout=5)
    r.raise_for_status()
    return r.json()


def check_model():
    matches=[m for m in get('tags')['models'] if m['name']==MODEL]
    if len(matches)!=1 or matches[0]['digest']!=DIGEST:
        raise ValueError('model_digest_mismatch')


class MeasuredClient(LocalLLMClient):
    def __init__(self,run):
        super().__init__(MODEL,BASE)
        self.run=run
        self.calls=0
        self.metrics={}

    def generate(self,prompt,system_prompt=None,json_mode=False,temperature=0.2):
        if self.calls: raise ValueError('one_request_budget_exhausted')
        self.calls+=1
        check_model()
        payload=dict(model=MODEL,prompt=prompt,system=system_prompt,stream=False,
            format='json',think=False,keep_alive=0,options=OPTIONS)
        write_json(self.run/'request.json',payload)
        began=time.perf_counter()
        try:
            response=requests.post(BASE+'/api/generate',json=payload,timeout=(5,180))
            with (self.run/'response.raw').open('xb') as f:f.write(response.content)
            response.raise_for_status()
            data=response.json()
            write_json(self.run/'response.json',data)
            self.metrics={k:data.get(k) for k in ['prompt_eval_count','eval_count','total_duration',
                'load_duration','prompt_eval_duration','eval_duration','done','done_reason']}
            check_model()
            if data.get('done') is not True or data.get('done_reason')!='stop':
                raise ValueError('incomplete_or_truncated_generation')
            # Never substitute reasoning text for the final answer; never repair malformed JSON.
            answer=json.loads(data['response'])
            return {'json':answer}
        finally:
            self.metrics['wall_seconds']=time.perf_counter()-began
            self.metrics['generation_requests']=self.calls
            write_json(self.run/'metrics.json',self.metrics)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--anchor',type=Path,required=True)
    args=parser.parse_args()
    run=args.run.resolve()
    if run.exists() or args.anchor.exists(): raise FileExistsError('run_or_anchor_exists')
    check_model()
    ps=get('ps')
    if ps.get('models'): raise ValueError('ollama_busy')
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
    memory,util=map(int,gpu.split(','))
    if memory>6000 or util>20:raise ValueError('gpu_busy')
    run.mkdir(parents=True,exist_ok=False)
    lock=ROOT/'.benchmarks/cosmoslov-gpu.lock'
    with lock.open('x',encoding='utf-8') as f:f.write(str(run))
    try:
        write_json(run/'preflight.json',dict(model=MODEL,digest=DIGEST,ps=ps,gpu=gpu,
            ollama_version=get('version'),executor_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            limits=dict(generation_requests=1,output_tokens=512,read_timeout_seconds=180)))
        conn=sqlite3.connect((ROOT/'data/scifi_lexicon.db').as_uri()+'?mode=ro',uri=True)
        try:
            row=conn.execute('SELECT w.id,w.title_orig,w.text_path,a.name_orig FROM works w JOIN authors a ON a.id=w.author_id WHERE w.id=15').fetchone()
        finally:conn.close()
        write_json(run/'work.json',dict(work_id=row[0],title=row[1],original_path=row[2],author=row[3]))
        checked_copy(row[2],run/'corpus/source.txt')
        checked_copy(Path(row[2]).with_name('zones.json'),run/'corpus/zones.json')
        for name in ['scripts/run_local_pilot.py','modules/corpus/queue.py','modules/corpus/witness.py',
            'modules/autoresearch/llm_client.py','modules/audit/exometric.py','docs/LOCAL_PILOT_PROTOCOL_V1.md','tests/test_local_pilot.py']:
            checked_copy(ROOT/name,run/'executor'/name)
        queue=CorpusQueue(run/'queue.db')
        profile=json.dumps(dict(model_digest=DIGEST,options=OPTIONS,think=False,
            executor_sha=sha(Path(__file__)),client_sha=sha(ROOT/'modules/autoresearch/llm_client.py')),sort_keys=True)
        pid=queue.prepare(row[0],run/'corpus/source.txt',profile)
        write_json(run/'progress_before.json',queue.status(pid))
        client=MeasuredClient(run)
        result=queue.run(pid,client,row[1],row[3],max_windows=1)
        write_json(run/'result.json',result)
        localizations=[]
        with queue.connect() as c:
            jobs=[dict(r) for r in c.execute("SELECT * FROM jobs WHERE state='done' ORDER BY id")]
        for job in jobs:
            text=queue.fragment(job)
            for term in json.loads(job['result_json']):
                matches=find_occurrences(text.encode('utf-8'),term)
                localizations.append(dict(term=term,status='present_in_fragment' if matches else 'absent_in_fragment',
                    positions=[dict(byte_start=job['start']+offset,matched_form=form) for offset,form in matches]))
        write_json(run/'candidate_localization.json',dict(results=localizations,
            boundary='Presence only, not proof of terminology, first attestation or scientific validity.'))
        write_json(run/'postflight.json',dict(ps=get('ps')))
        # Explicitly close/reopen SQLite for a portable stable checkpoint.
        with sqlite3.connect(run/'queue.db') as c:c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        for name,(source,expected) in PINS.items():checked_copy(source,run/'tools'/name,expected)
        anchor=seal_prepared_bundle(run,args.anchor)
        print(json.dumps(dict(result=result,metrics=client.metrics,localizations=localizations,anchor=anchor),ensure_ascii=False))
    finally:
        lock.unlink()


if __name__=='__main__':
    main()
