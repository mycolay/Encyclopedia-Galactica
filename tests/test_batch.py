import json
import sqlite3
import time
from pathlib import Path
import pytest
from modules.autoresearch import batch
from scripts.apply_t8 import SCHEMA_T8_SQL


def test_budget_reservation_and_error_stops(tmp_path):
    c=batch.BatchClient(tmp_path,max_input=8192,max_output=512)
    assert c.stop_reason() is None
    c.input_tokens=1
    assert c.stop_reason()=='input_budget'
    c.input_tokens=0;c.output_tokens=1
    assert c.stop_reason()=='output_budget'
    c.output_tokens=0;c.consecutive=3
    assert c.stop_reason()=='consecutive_errors'
    c.consecutive=0;c.calls=10;c.errors=2
    assert c.stop_reason()=='error_rate'


def test_localization_utf8_boundaries_and_absence():
    data='Вступ. Робот рухається. Кінець'.encode()
    job={'start':len('Вступ. '.encode()),'end':len(data)}
    r=batch.localize(data,job,'Робот')
    assert r and r['quote'].startswith('Робот')
    assert r['byte_start']>=job['start']
    assert batch.localize(data,job,'Вступ') is None


def test_append_idempotent_and_proposal_not_verified():
    c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE terms(id INTEGER PRIMARY KEY)');c.executescript(SCHEMA_T8_SQL)
    r=batch.localize(b'robot works',{'start':0,'end':11},'robot')
    r.update(work_id=1,year=1920,verified_at_utc='test',proposal=dict(proposed_ukr_term='Робот',
        derivation_model='working hypothesis',stylistic_note='needs review',scientific_definition='draft'))
    assert batch.insert_records(c,[r])==1
    assert batch.insert_records(c,[r])==0
    assert c.execute('SELECT COUNT(*) FROM attestations').fetchone()[0]==2
    assert c.execute("SELECT verified_at_utc FROM attestations WHERE register='proposed'").fetchone()[0] is None


def test_timeout_charges_reserved_tokens(tmp_path,monkeypatch):
    monkeypatch.setattr(batch,'check_model',lambda:None)
    monkeypatch.setattr(batch,'get',lambda key:{'models':[]})
    def fail(*a,**kw):raise TimeoutError('timeout')
    monkeypatch.setattr(batch.requests,'post',fail)
    c=batch.BatchClient(tmp_path)
    with pytest.raises(TimeoutError):c.propose_candidates('text')
    assert c.input_tokens==8192 and c.output_tokens==512 and c.errors==1
    assert (tmp_path/'calls/0001/metric.json').exists()
