"""Local encyclopedia and append-only human audit journal."""
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request, session, send_from_directory

ROOT=Path(__file__).resolve().parent
TRANSLATIONS={'Nadrobot':'superrobot','nervy na bolest':'pain-sensing nerves',
              'Rossumových závodů':"Rossum’s factories",'robot':'robot'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def catalog():
    raw=json.loads((ROOT/'docs/SCI_FI_LEXICON.json').read_text(encoding='utf-8'))
    with sqlite3.connect((ROOT/'data/scifi_lexicon.db').as_uri()+'?mode=ro',uri=True) as c:
        languages=dict(c.execute('SELECT id,original_lang FROM works'))
    c.close()
    reviews=json.loads((ROOT/'docs/GREAT_ATTRACTOR_REVIEW_V1.json').read_text(encoding='utf-8'))
    decisions={x['id']:x for x in reviews['items']}
    contexts=json.loads((ROOT/'docs/CALIBRATION_CONTEXTS_STEP11.json').read_text(encoding='utf-8'))
    cards=[]
    for item in raw['cards']:
        card=dict(item)
        card['id']='lex-'+digest([card['work_id'],card['term']])[:20]
        card['kind']='candidate';card['recommendations']=[]
        for p in card['proposals']:
            key=hashlib.sha256(('review.v1:'+str(p['id'])).encode()).hexdigest()[:16]
            if key in decisions:
                d=decisions[key];card['recommendations'].append(d)
                if d['route']=='organization':card['kind']='organization'
                elif d['relevance']=='include':card['kind']='concept'
                if key in contexts and contexts[key]['excerpts']:
                    card['attestations']=[dict(x,artifact_sha256=x['source_sha256'],check='byte_verified_zone_map_checked') for x in contexts[key]['excerpts']]
        card['language']=languages.get(card['work_id'],'unknown')
        card['english']=dict(value=card['term'],status='original') if card['language']=='en' else dict(value=TRANSLATIONS.get(card['term'],''),status='working_translation' if card['term'] in TRANSLATIONS else 'missing')
        card['ukrainian']=card['proposals'][0]['variant'] if card['proposals'] else ''
        card['status']='research_draft';cards.append(card)
    reference=json.loads((ROOT/'docs/WORLD_REFERENCE_DRAFT_V1.json').read_text(encoding='utf-8'))
    for item in reference['entities']:
        if item['kind'] not in ('place','character'):continue
        cards.append(dict(id='world-'+digest([item['scene'],item['name']])[:20],term=item['name'],
            kind=item['kind'],title='Frankenstein; or, The Modern Prometheus',author='Mary Shelley',work_id=14,
            language='en',english=dict(value=item['name'],status='original'),ukrainian='',
            definition=dict(text=item['description_uk'],status='assistant_draft'),
            status='assistant_draft',attestations=[dict(quote=item['quote'],check='reference_draft',artifact_sha256=reference['source_sha256'])],
            proposals=[],recommendations=[dict(reason=item['note'],relevance='uncertain')]))
    preferred=json.loads((ROOT/'docs/PREFERRED_TRANSLATIONS_V1.json').read_text(encoding='utf-8'))
    for card in cards:
        for choice in preferred['items']:
            if (choice['work_id'],choice['term'],choice['kind'])!=(card['work_id'],card['term'],card['kind']):continue
            if not any(a.get('artifact_sha256')==choice['source_sha256'] for a in card['attestations']):continue
            card['ukrainian']=choice['ukrainian']
            card['preferred_translation']=dict(choice,status='assistant_recommendation',reviewer='Great Attractor')
    cards.sort(key=lambda c:(0 if c['term']=='Nadrobot' else 1 if c['recommendations'] else 2,c['term'].casefold()))
    for card in cards:card['revision']=digest(card)
    return cards


def create_app(audit_path=None):
    app=Flask(__name__,static_folder=str(ROOT/'web'),static_url_path='/static')
    app.secret_key=secrets.token_hex(32)
    app.config.update(MAX_CONTENT_LENGTH=16000,SESSION_COOKIE_SAMESITE='Strict',SESSION_COOKIE_HTTPONLY=True)
    audit_path=Path(audit_path or ROOT/'data/editorial_audit.db')
    def connect():
        c=sqlite3.connect(audit_path);c.row_factory=sqlite3.Row
        c.execute('CREATE TABLE IF NOT EXISTS decisions (event_id TEXT PRIMARY KEY, card_id TEXT NOT NULL, revision TEXT NOT NULL, action TEXT NOT NULL, note TEXT NOT NULL, ukrainian TEXT NOT NULL, english TEXT NOT NULL, created_at TEXT NOT NULL)')
        c.commit();return c
    def history():
        with connect() as c:rows=[dict(x) for x in c.execute('SELECT * FROM decisions ORDER BY rowid')]
        c.close();return rows

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        return response

    @app.get('/')
    def home():return send_from_directory(ROOT/'web','index.html')

    @app.get('/api/catalog')
    def listing():
        session.setdefault('csrf',secrets.token_hex(24))
        return jsonify(cards=catalog(),history=history(),csrf=session['csrf'])

    @app.post('/api/decisions')
    def save():
        if not session.get('csrf') or request.headers.get('X-CSRF-Token')!=session['csrf']:
            return jsonify(error='Онови сторінку: сеанс змінився.'),403
        if request.headers.get('Origin') not in (None,request.host_url.rstrip('/')):
            return jsonify(error='Інше походження запиту.'),403
        data=request.get_json(silent=True)
        if not isinstance(data,dict):return jsonify(error='Некоректний запит.'),400
        keys=('event_id','card_id','revision','action','note','ukrainian','english')
        if any(not isinstance(data.get(k),str) for k in keys):return jsonify(error='Некоректні поля.'),400
        if any(len(data[k])>4000 for k in keys) or not 8<=len(data['event_id'])<=80:return jsonify(error='Завеликий запис.'),400
        if data['action'] not in ('accept','revise','reject','context'):return jsonify(error='Невідома дія.'),400
        if data['action']!='accept' and not data['note'].strip():return jsonify(error='Додай пояснення рішення.'),400
        card=next((c for c in catalog() if c['id']==data['card_id']),None)
        if not card:return jsonify(error='Картку не знайдено.'),404
        if card['revision']!=data['revision']:return jsonify(error='Джерельна картка змінилася. Онови сторінку.'),409
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            previous=c.execute('SELECT * FROM decisions WHERE event_id=?',(data['event_id'],)).fetchone()
            if previous:
                if any(previous[k]!=data[k] for k in keys):return jsonify(error='Конфлікт ідентифікатора рішення.'),409
                return jsonify(saved=dict(previous),duplicate=True)
            now=datetime.now(timezone.utc).isoformat()
            c.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)',tuple(data[k] for k in keys)+(now,))
        c.close()
        return jsonify(saved=dict(data,created_at=now)),201

    @app.get('/api/audit-export')
    def export():return jsonify(schema='cosmoslov.local_audit.v1',decisions=history(),claim='Human UI decisions; no automatic source-database promotion')
    return app


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8767);args=p.parse_args()
    create_app().run(host='127.0.0.1',port=args.port,debug=False)
