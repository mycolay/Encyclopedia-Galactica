import json
import hashlib
import pytest
from modules.corpus.queue import CorpusQueue
from modules.autoresearch.llm_client import LocalLLMClient


def corpus(tmp_path,text='Передмова. Робот летить. Кінець.',prefix='Передмова. '):
    p=tmp_path/'source.txt';p.write_bytes(text.encode())
    z={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'zones':[
        {'kind':'body','byte_start':len(prefix.encode()),'byte_end':len(text.encode())}]}
    p.with_name('zones.json').write_text(json.dumps(z),encoding='utf-8')
    q=CorpusQueue(tmp_path/'queue.db')
    pid=q.prepare(1,p,'test-profile',window_size=8,overlap=3)
    return q,pid,p


class Empty:
    def propose_candidates(self,*args): return []


def test_resume_unicode_overlap_and_tail(tmp_path):
    q,pid,p=corpus(tmp_path)
    first=q.run(pid,Empty(),max_windows=1)
    assert 0<first['progress']['coverage']<1
    q=CorpusQueue(q.path)
    q.run(pid,Empty(),max_windows=50)
    s=q.status(pid)
    assert s['coverage']==1 and s['extraction_complete']
    assert s['completed_bytes']==len(p.read_bytes())-len('Передмова. '.encode())
    assert q.run(pid,Empty(),max_windows=1)['completed_this_run']==0


def test_lease_exclusive_recovery_and_stale_completion(tmp_path):
    q,pid,_=corpus(tmp_path)
    a=q.claim(pid,lease_seconds=10,now=100)
    b=q.claim(pid,lease_seconds=10,now=100)
    assert a['id']!=b['id']
    recovered=q.claim(pid,lease_seconds=10,now=111)
    assert recovered['id']==a['id'] and recovered['token']!=a['token']
    with pytest.raises(ValueError,match='stale_lease'): q.finish(a,result=[],now=112)
    q.finish(recovered,result=['Робот'],now=112)


def test_error_not_coverage_and_retry_ceiling(tmp_path):
    q,pid,_=corpus(tmp_path)
    class Broken:
        def propose_candidates(self,*args): raise RuntimeError('network failed')
    for _ in range(3): assert q.run(pid,Broken(),max_windows=50)['status']=='error'
    s=q.status(pid)
    assert s['completed_bytes']==0
    with q.connect() as c: assert c.execute('SELECT attempts FROM jobs ORDER BY id LIMIT 1').fetchone()[0]==3
    q.run(pid,Empty(),max_windows=50)
    assert not q.status(pid)['extraction_complete']


def test_source_drift_new_plan_and_idempotency(tmp_path):
    q,pid,p=corpus(tmp_path)
    assert q.prepare(1,p,'test-profile',8,3)==pid
    before=q.status(pid)['total_jobs']
    q.prepare(1,p,'test-profile',8,3)
    assert q.status(pid)['total_jobs']==before
    job=q.claim(pid)
    p.write_bytes(p.read_bytes()+b'!')
    with pytest.raises(ValueError,match='drift'):q.fragment(job)
    z=json.loads(p.with_name('zones.json').read_text());z['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    p.with_name('zones.json').write_text(json.dumps(z))
    new=q.prepare(1,p,'test-profile',8,3)
    assert new!=pid and q.status(new)['completed_bytes']==0


def test_multiple_body_regions_excludes_gap(tmp_path):
    q,_,p=corpus(tmp_path,'abcXYZdef','')
    z={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'zones':[
        {'kind':'body','byte_start':0,'byte_end':3},{'kind':'body','byte_start':6,'byte_end':9}]}
    p.with_name('zones.json').write_text(json.dumps(z))
    pid=q.prepare(1,p,'regions',8,3)
    q.run(pid,Empty(),max_windows=10)
    assert q.status(pid)['completed_bytes']==6


def test_malformed_llm_output_not_empty_success(monkeypatch):
    client=LocalLLMClient()
    for invalid in [{'json':{}},{'json':{'candidates':'x'}},{'json':{'candidates':[42]}}]:
        monkeypatch.setattr(client,'generate',lambda **kw:invalid)
        with pytest.raises(ValueError):client.propose_candidates('text')
    def fail(**kw):raise RuntimeError('timeout')
    monkeypatch.setattr(client,'generate',fail)
    with pytest.raises(RuntimeError):client.propose_candidates('text')
    monkeypatch.setattr(client,'generate',lambda **kw:{'json':{'candidates':[]}})
    assert client.propose_candidates('text')==[]
