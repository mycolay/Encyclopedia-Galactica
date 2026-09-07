"""Bounded batch primitives: budgeted local inference and source-backed candidates."""
import hashlib
import json
import time
from pathlib import Path
import requests
from modules.autoresearch.llm_client import LocalLLMClient
from modules.corpus.witness import find_occurrences,snap_to_utf8_boundary
from modules.audit.exometric import write_json
from scripts.run_local_pilot import MODEL,DIGEST,OPTIONS,BASE,check_model,get


class BatchClient(LocalLLMClient):
    def __init__(self,run,max_input=300000,max_output=20000,max_seconds=3600):
        super().__init__(MODEL,BASE)
        self.run=Path(run);self.started=time.monotonic()
        self.max_input=max_input;self.max_output=max_output;self.max_seconds=max_seconds
        self.input_tokens=0;self.output_tokens=0;self.calls=0;self.errors=0;self.consecutive=0
        self.metrics=[];self.stage='extract'

    def stop_reason(self):
        if time.monotonic()-self.started>=self.max_seconds:return 'time_budget'
        if self.input_tokens+8192>self.max_input:return 'input_budget'
        if self.output_tokens+512>self.max_output:return 'output_budget'
        if self.consecutive>=3:return 'consecutive_errors'
        if self.calls>=10 and self.errors/self.calls>0.10:return 'error_rate'
        return None

    def generate(self,prompt,system_prompt=None,json_mode=True,temperature=0.2):
        reason=self.stop_reason()
        if reason:raise RuntimeError(reason)
        check_model()
        if any(m.get('digest')!=DIGEST for m in get('ps').get('models',[])):
            raise RuntimeError('gpu_model_conflict')
        self.calls+=1
        folder=self.run/'calls'/('%04d'%self.calls);folder.mkdir(parents=True)
        payload=dict(model=MODEL,prompt=prompt,system=system_prompt,stream=False,format='json',
                     think=False,keep_alive='10m',options=dict(OPTIONS,temperature=temperature))
        write_json(folder/'request.json',payload)
        before=time.perf_counter();data={};error=None
        try:
            response=requests.post(BASE+'/api/generate',json=payload,timeout=(5,180))
            (folder/'response.raw').write_bytes(response.content)
            response.raise_for_status();data=response.json()
            check_model()
            if data.get('done') is not True or data.get('done_reason')!='stop':raise ValueError('incomplete_generation')
            answer=json.loads(data['response'])
            if self.stage=='extract':
                if not isinstance(answer,dict) or not isinstance(answer.get('candidates'),list) or any(not isinstance(x,str) or not x.strip() for x in answer['candidates']):
                    raise ValueError('invalid_candidates')
            else:
                if not isinstance(answer,dict) or any(not isinstance(answer.get(k),str) or not answer[k].strip() for k in ['scientific_definition','proposed_ukr_term','derivation_model','stylistic_note']):
                    raise ValueError('invalid_derivation')
            self.consecutive=0
            return {'json':answer}
        except Exception as exc:
            error=str(exc);self.errors+=1;self.consecutive+=1
            raise
        finally:
            # Unknown consumption is charged at its reserved maximum, never zero.
            inp=data.get('prompt_eval_count',8192);out=data.get('eval_count',512)
            inp=inp if isinstance(inp,int) and inp>=0 else 8192
            out=out if isinstance(out,int) and out>=0 else 512
            self.input_tokens+=inp;self.output_tokens+=out
            metric=dict(call=self.calls,stage=self.stage,wall_seconds=time.perf_counter()-before,
                prompt_tokens=inp,output_tokens=out,error=error,
                token_counts_observed='prompt_eval_count' in data and 'eval_count' in data,
                durations_ns={k:data.get(k) for k in ['total_duration','load_duration','prompt_eval_duration','eval_duration']})
            self.metrics.append(metric);write_json(folder/'metric.json',metric)


def localize(data,job,term):
    """Locate only within the processed body window; clamp quote to that same span."""
    matches=find_occurrences(data[job['start']:job['end']],term)
    if not matches:return None
    offset,form=matches[0];pos=job['start']+offset
    start=snap_to_utf8_boundary(data,max(job['start'],pos-100),'forward')
    end=snap_to_utf8_boundary(data,min(job['end'],max(pos+len(form.encode()),start+320)),'backward')
    window=data[start:end]
    if not find_occurrences(window,term):return None
    return dict(term_orig=term,artifact_sha256=hashlib.sha256(data).hexdigest(),
        byte_start=start,byte_len=len(window),window_sha256=hashlib.sha256(window).hexdigest(),
        matched_form=form,zone='body',quote=window.decode('utf-8'))


def insert_records(conn,records):
    """Append lexical evidence and unreviewed proposals; idempotent by source/work/term."""
    existing={(r[0],r[1],r[2].casefold()) for r in conn.execute(
        "SELECT work_id,artifact_sha256,term_orig FROM attestations WHERE register='attested'")}
    added=0
    for r in records:
        key=(r['work_id'],r['artifact_sha256'],r['term_orig'].casefold())
        if key in existing:continue
        cols=['term_orig','work_id','year','zone','matched_form','artifact_sha256','byte_start','byte_len','window_sha256']
        values={k:r[k] for k in cols}
        values.update(register='attested',cts_urn=f"urn:cts:cosmoslov:{r['work_id']}:{r['byte_start']}+{r['byte_len']}",
                      verified_at_utc=r['verified_at_utc'],verifier_version='batch.v1.lexical_only')
        conn.execute('INSERT INTO attestations('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',list(values.values()))
        if r.get('proposal'):
            p=r['proposal']
            conn.execute('INSERT INTO attestations(term_orig,work_id,year,register,proposed_ukr_term,derivation_model,stylistic_note,proposed_by_model) VALUES(?,?,?,?,?,?,?,?)',
                (r['term_orig'],r['work_id'],r['year'],'proposed',p['proposed_ukr_term'],p['derivation_model'],
                 'Чернетка визначення: '+p['scientific_definition']+'\n'+p['stylistic_note'],MODEL+'@'+DIGEST))
        existing.add(key);added+=1
    return added
