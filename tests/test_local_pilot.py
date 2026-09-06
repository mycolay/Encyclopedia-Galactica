import json
import pytest
from scripts import run_local_pilot as pilot


class Response:
    def __init__(self,reason='stop',answer='{"candidates":["Time Traveller"]}'):
        self.data=dict(done=True,done_reason=reason,response=answer,prompt_eval_count=123,eval_count=12,
            eval_duration=1000000000,total_duration=2000000000)
        self.content=json.dumps(self.data).encode()
    def raise_for_status(self):pass
    def json(self):return self.data


def test_exact_payload_metrics_and_one_call(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot,'check_model',lambda:None)
    calls=[]
    def post(url,**kw):calls.append(kw);return Response()
    monkeypatch.setattr(pilot.requests,'post',post)
    client=pilot.MeasuredClient(tmp_path)
    assert client.propose_candidates('text')==['Time Traveller']
    payload=calls[0]['json']
    assert payload['keep_alive']==0 and payload['think'] is False
    assert payload['options']['num_predict']==512
    assert json.loads((tmp_path/'metrics.json').read_text())['eval_count']==12
    with pytest.raises(ValueError,match='budget'):client.propose_candidates('again')
    assert len(calls)==1


@pytest.mark.parametrize('reason,answer',[('length','{"candidates":[]}'),('stop','broken JSON')])
def test_invalid_result_preserves_evidence(tmp_path,monkeypatch,reason,answer):
    monkeypatch.setattr(pilot,'check_model',lambda:None)
    monkeypatch.setattr(pilot.requests,'post',lambda *a,**kw:Response(reason,answer))
    with pytest.raises(ValueError):pilot.MeasuredClient(tmp_path).propose_candidates('text')
    assert (tmp_path/'response.raw').exists() and (tmp_path/'metrics.json').exists()


def test_timeout_is_recorded(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot,'check_model',lambda:None)
    def fail(*a,**kw):raise TimeoutError('timeout')
    monkeypatch.setattr(pilot.requests,'post',fail)
    with pytest.raises(TimeoutError):pilot.MeasuredClient(tmp_path).propose_candidates('text')
    assert json.loads((tmp_path/'metrics.json').read_text())['generation_requests']==1
