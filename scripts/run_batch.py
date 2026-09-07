"""Execute a bounded extraction batch, stage/export/seal evidence, then append to catalog."""
import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from modules.autoresearch.batch import BatchClient,localize,insert_records,MODEL,DIGEST,BASE,get,check_model
from modules.corpus.queue import CorpusQueue
from modules.audit.exometric import PINS,checked_copy,write_json,sha,seal_prepared_bundle
from modules.lexicography.dictionary_exporter import DictionaryExporter,check_quote
from modules.lexicography.relevance import select_derivations


def backup(source,target):
    src=sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(target)
    try:src.backup(dst)
    finally:dst.close();src.close()
    # Immutable artifacts must be self-contained, without volatile WAL/SHM sidecars.
    snapshot=sqlite3.connect(target)
    try:
        if snapshot.execute('PRAGMA journal_mode=DELETE').fetchone()[0]!='delete':
            raise ValueError('snapshot_journal_normalization_failed')
    finally:snapshot.close()


def logical_hash(c):
    return hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--anchor',type=Path,required=True)
    parser.add_argument('--queue',type=Path,default=ROOT/'data/batch_queue.db')
    parser.add_argument('--windows',type=int,default=32)
    parser.add_argument('--relevance-decisions',type=Path)
    args=parser.parse_args()
    if not 1<=args.windows<=120:raise ValueError('window_budget')
    run=args.run.resolve()
    if run.exists() or args.anchor.exists():raise FileExistsError('immutable_run_exists')
    check_model();ps=get('ps')
    if ps.get('models'):raise ValueError('ollama_busy')
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
    memory,util=map(int,gpu.split(','))
    if memory>6000 or util>40:raise ValueError('gpu_busy')
    if shutil.disk_usage(ROOT).free<2*1024**3:raise ValueError('low_disk')
    lock=ROOT/'.benchmarks/cosmoslov-gpu.lock'
    with lock.open('x') as f:f.write(str(run))
    try:
        run.mkdir(parents=True)
        decisions={}
        if args.relevance_decisions:
            checked_copy(args.relevance_decisions,run/'relevance-decisions.json')
            decisions=json.loads((run/'relevance-decisions.json').read_text(encoding='utf-8'))
            if not isinstance(decisions,dict):raise ValueError('invalid_relevance_decisions')
        else:write_json(run/'relevance-decisions.json',decisions)
        main_db=ROOT/'data/scifi_lexicon.db'
        backup(main_db,run/'baseline.db')
        c=sqlite3.connect(run/'baseline.db');c.row_factory=sqlite3.Row
        baseline_hash=logical_hash(c)
        works=[dict(r) for r in c.execute('SELECT w.*,a.name_orig author_name FROM works w JOIN authors a ON a.id=w.author_id WHERE has_full_text=1 ORDER BY cult_score DESC,w.id')]
        known={(r[0],r[1],r[2].casefold()) for r in c.execute("SELECT work_id,artifact_sha256,term_orig FROM attestations WHERE register='attested'")};c.close()
        names=['scripts/run_batch.py','modules/autoresearch/batch.py','scripts/run_local_pilot.py',
            'modules/corpus/queue.py','modules/corpus/witness.py','modules/autoresearch/llm_client.py',
            'modules/audit/exometric.py','modules/lexicography/dictionary_exporter.py',
            'docs/BATCH_AND_EDITORIAL_PROTOCOL_V1.md','docs/BATCH_EXECUTION_V1.md','tests/test_batch.py',
            'modules/lexicography/relevance.py','tests/test_relevance.py']
        for name in names:checked_copy(ROOT/name,run/'executor'/name)
        queue=CorpusQueue(args.queue)
        profile=json.dumps(dict(model=DIGEST,worker=sha(ROOT/'modules/autoresearch/batch.py'),
            client=sha(ROOT/'modules/autoresearch/llm_client.py'),version='batch.v1'),sort_keys=True)
        plans=[]
        for w in works:
            path=run/'corpus'/str(w['id'])/'source.txt'
            checked_copy(w['text_path'],path);checked_copy(Path(w['text_path']).with_name('zones.json'),path.with_name('zones.json'))
            pid=queue.prepare(w['id'],path,profile)
            plans.append((w,pid,path))
        write_json(run/'contract.json',dict(executor_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            model=DIGEST,windows=args.windows,max_derivations=16,gpu=gpu,ollama=get('version'),
            plans=[queue.status(pid) for _,pid,_ in plans],baseline_logical_sha256=baseline_hash,
            derivation_policy='human_context_relevance.v1',relevance_decisions_sha256=sha(run/'relevance-decisions.json')))
        client=BatchClient(run)
        records=[];outcomes=[];done=0;stop=None;seen=set(known)
        for w,pid,path in plans:
            while done<args.windows and not client.stop_reason() and not stop:
                job=queue.claim(pid,max_attempts=2)
                if job is None:break
                try:
                    text=queue.fragment(job)
                    candidates=client.propose_candidates(text,w['title_orig'],w['author_name'])
                    queue.fragment(job)
                    queue.finish(job,result=candidates);done+=1
                except Exception as exc:
                    queue.finish(job,error=str(exc))
                    outcomes.append(dict(job=job['id'],error=str(exc)))
                    if any(key in str(exc) for key in ['drift','mismatch','conflict','out of memory','OOM']):stop=str(exc)
                    continue
                data=path.read_bytes()
                for term in candidates:
                    record=localize(data,job,term)
                    outcome=dict(work_id=w['id'],job=job['id'],term=term,status='absent_in_fragment')
                    if record:
                        key=(w['id'],record['artifact_sha256'],term.casefold())
                        outcome['status']='existing_or_duplicate' if key in seen else 'new_lexical_evidence'
                        if key not in seen:
                            record.update(work_id=w['id'],year=w['year'],author=w['author_name'],title=w['title_orig'],
                                verified_at_utc=datetime.now(timezone.utc).isoformat(),source_path=str(path),proposal=None)
                            quote,reason=check_quote(record,path)
                            if quote is None:raise ValueError('localization_check_failed:'+reason)
                            records.append(record);seen.add(key)
                    outcomes.append(outcome)
                print(json.dumps(dict(completed_windows=done,calls=client.calls,new_evidence=len(records),work=w['title_orig'])),flush=True)
            if done>=args.windows or client.stop_reason() or stop:break
        # Rebuild from durable results, including done jobs from an interrupted earlier batch.
        records=[];seen=set(known)
        for w,pid,path in plans:
            with queue.connect() as c:
                completed=[dict(r) for r in c.execute("SELECT * FROM jobs WHERE plan_id=? AND state='done' ORDER BY start",(pid,))]
            data=path.read_bytes()
            for job in completed:
                queue.fragment(job)
                for term in json.loads(job['result_json']):
                    record=localize(data,job,term)
                    if not record:continue
                    key=(w['id'],record['artifact_sha256'],term.casefold())
                    if key in seen:continue
                    record.update(work_id=w['id'],year=w['year'],author=w['author_name'],title=w['title_orig'],
                        verified_at_utc=datetime.now(timezone.utc).isoformat(),source_path=str(path),proposal=None)
                    if check_quote(record,path)[0] is None:raise ValueError('recovered_evidence_invalid')
                    records.append(record);seen.add(key)
        # No derivation until a context-bound human relevance decision exists.
        eligible,held=select_derivations(records,decisions)
        write_json(run/'derivation-selection.json',dict(eligible_count=len(eligible),held=held))
        client.stage='derive'
        if not stop and not client.stop_reason():
            for record in eligible:
                if client.stop_reason():break
                try:
                    prompt='Термін: '+record['term_orig']+'\nТвір: '+record['title']+'\nКонтекст:\n'+record['quote']
                    system=('Ти готуєш українську лексикографічну ЧЕРНЕТКУ. Поясни значення лише за контекстом. '
                        'Запропонуй зрозумілий український відповідник, не обов’язково новотвір. '
                        'Не вигадуй посилань на словники, перекладачів чи видання. '
                        'Якщо слово загальне або контекст недостатній, прямо зазнач це у stylistic_note. '
                        'Поверни JSON з непорожніми рядками scientific_definition, proposed_ukr_term, derivation_model, stylistic_note.')
                    record['proposal']=client.generate(prompt,system)['json']
                except Exception as exc:
                    outcomes.append(dict(term=record['term_orig'],stage='derive',error=str(exc)))
                    if any(key in str(exc) for key in ['mismatch','conflict','out of memory','OOM']):stop=str(exc);break
        try:
            response=requests.post(BASE+'/api/generate',json={'model':MODEL,'keep_alive':0},timeout=15)
            unload=dict(status=response.status_code)
        except Exception as exc:unload=dict(error=str(exc))
        write_json(run/'outcomes.json',outcomes);write_json(run/'records.json',records)
        summary=dict(completed_windows=done,new_lexical_evidence=len(records),ukrainian_drafts=sum(bool(r['proposal']) for r in records),
            calls=client.calls,errors=client.errors,input_tokens=client.input_tokens,output_tokens=client.output_tokens,
            elapsed_seconds=time.monotonic()-client.started,stop_reason=stop or client.stop_reason() or 'window_budget_or_queue_end',
            metrics=client.metrics,unload=unload,progress=[queue.status(pid) for _,pid,_ in plans])
        write_json(run/'summary.json',summary)
        backup(args.queue,run/'queue.db')
        backup(run/'baseline.db',run/'snapshot.db')
        with sqlite3.connect(run/'snapshot.db') as c:
            for w,_,p in plans:c.execute('UPDATE works SET text_path=? WHERE id=?',(str(p),w['id']))
            assert insert_records(c,records)==len(records)
        c.close()  # Close WAL writers before sealing the immutable SQLite snapshot.
        exporter=DictionaryExporter(SimpleNamespace(db_path=run/'snapshot.db'),run/'SCI_FI_LEXICON.md');exporter.export_markdown()
        for name,(source,expected) in PINS.items():checked_copy(source,run/'tools'/name,expected)
        anchor=seal_prepared_bundle(run,args.anchor)
        # Commit only append-only records after source and baseline rechecks. Never overwrite catalog.
        with sqlite3.connect(main_db) as c:
            c.execute('BEGIN IMMEDIATE')
            if logical_hash(c)!=baseline_hash:raise ValueError('catalog_changed_during_batch_staged_output_retained')
            for r in records:
                original=next(w['text_path'] for w in works if w['id']==r['work_id'])
                if check_quote(r,original)[0] is None:raise ValueError('original_changed_before_publish')
            inserted=insert_records(c,records)
        c.close()
        for name in ['SCI_FI_LEXICON.md','SCI_FI_LEXICON.json']:
            (ROOT/'docs'/name).write_bytes((run/name).read_bytes())
        publication=dict(run=str(run),inserted_lexical_evidence=inserted,ukrainian_drafts=summary['ukrainian_drafts'],anchor=anchor,
            claim='Lexical presence verified; concept relevance, definitions and Ukrainian drafts await editorial review.')
        write_json(ROOT/'docs'/(run.name+'-publication.json'),publication)
        print(json.dumps(publication,ensure_ascii=False),flush=True)
    finally:
        if 'client' in locals() and client.calls and 'unload' not in locals():
            try:requests.post(BASE+'/api/generate',json={'model':MODEL,'keep_alive':0},timeout=15)
            except Exception:pass
        lock.unlink()


if __name__=='__main__':main()
