import sqlite3
from encyclopedia import create_app,catalog

def client(tmp_path):
    app=create_app(tmp_path/'audit.db');app.config['TESTING']=True
    c=app.test_client();data=c.get('/api/catalog').get_json()
    return c,data

def payload(data):
    card=data['cards'][0]
    return dict(event_id='test-event-0001',card_id=card['id'],revision=card['revision'],action='revise',note='TEST ONLY',ukrainian='TEST',english='TEST')

def test_catalog_has_multilingual_status_and_all_sections():
    cards=catalog();assert len(cards)>=233
    assert {'concept','place','character','organization'} <= {c['kind'] for c in cards}
    assert all(c['english']['status'] in ('original','working_translation','missing') for c in cards)

def test_save_survives_new_session_and_retry(tmp_path):
    c,data=client(tmp_path);p=payload(data);headers={'X-CSRF-Token':data['csrf']}
    assert c.post('/api/decisions',json=p,headers=headers).status_code==201
    assert c.post('/api/decisions',json=p,headers=headers).get_json()['duplicate']
    other=create_app(tmp_path/'audit.db').test_client()
    assert len(other.get('/api/catalog').get_json()['history'])==1

def test_invalid_requests_and_cross_origin_cannot_write(tmp_path):
    c,data=client(tmp_path);p=payload(data)
    assert c.post('/api/decisions',json=p).status_code==403
    headers={'X-CSRF-Token':data['csrf'],'Origin':'https://other.invalid'}
    assert c.post('/api/decisions',json=p,headers=headers).status_code==403
    assert c.get('/api/audit-export').get_json()['decisions']==[]

def test_stale_revision_rejected(tmp_path):
    c,data=client(tmp_path);p=payload(data);p['revision']='stale'
    assert c.post('/api/decisions',json=p,headers={'X-CSRF-Token':data['csrf']}).status_code==409

def test_same_event_id_cannot_rewrite_history(tmp_path):
    c,data=client(tmp_path);p=payload(data);h={'X-CSRF-Token':data['csrf']}
    c.post('/api/decisions',json=p,headers=h);p['note']='changed'
    assert c.post('/api/decisions',json=p,headers=h).status_code==409
    assert c.get('/api/audit-export').get_json()['decisions'][0]['note']=='TEST ONLY'

def test_nonaccept_requires_note(tmp_path):
    c,data=client(tmp_path);p=payload(data);p['note']=' '
    assert c.post('/api/decisions',json=p,headers={'X-CSRF-Token':data['csrf']}).status_code==400

def test_shell_and_assets_available(tmp_path):
    c,_=client(tmp_path)
    for path in ['/','/static/app.js','/static/style.css']:assert c.get(path).status_code==200
