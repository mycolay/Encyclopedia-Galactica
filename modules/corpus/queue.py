"""Persistent, versioned extraction queue. Coverage means completed extraction only."""
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def union_size(spans):
    total, end = 0, -1
    for a,b in sorted(spans):
        total += max(0,b-max(a,end))
        end=max(end,b)
    return total


class CorpusQueue:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS plans(
                id TEXT PRIMARY KEY, work_id INTEGER NOT NULL, path TEXT NOT NULL,
                source_sha TEXT NOT NULL, zones_sha TEXT NOT NULL, profile TEXT NOT NULL,
                window_size INTEGER NOT NULL, overlap INTEGER NOT NULL, target_bytes INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(
                id INTEGER PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES plans(id),
                start INTEGER NOT NULL, end INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0, token TEXT, lease_until REAL,
                result_json TEXT, error TEXT, UNIQUE(plan_id,start,end));
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, at REAL NOT NULL,
                kind TEXT NOT NULL, detail TEXT NOT NULL);
            ''')

    def connect(self):
        c=sqlite3.connect(self.path,timeout=10)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        return c

    def prepare(self,work_id,path,profile,window_size=8000,overlap=200):
        if not profile or not isinstance(window_size,int) or not 0 <= overlap < window_size:
            raise ValueError('invalid_window_or_profile')
        path=Path(path).resolve(); data=path.read_bytes()
        zones_bytes=path.with_name('zones.json').read_bytes()
        zones=json.loads(zones_bytes)
        source_sha=digest(data)
        if zones.get('source_sha256') != source_sha:
            raise ValueError('zones_not_bound_to_source')
        spans=sorted((z['byte_start'],z['byte_end']) for z in zones['zones'] if z['kind']=='body')
        if not spans:
            raise ValueError('no_body')
        prev=0; windows=[]
        for start,end in spans:
            if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(data) or start<prev:
                raise ValueError('invalid_or_overlapping_body')
            prev=end
            text=data[start:end].decode('utf-8')
            offsets=[start]
            for ch in text: offsets.append(offsets[-1]+len(ch.encode('utf-8')))
            for pos in range(0,len(text),window_size-overlap):
                stop=min(pos+window_size,len(text))
                windows.append((offsets[pos],offsets[stop]))
                if stop==len(text): break
        values=dict(work_id=work_id,path=str(path),source_sha=source_sha,zones_sha=digest(zones_bytes),
                    profile=profile,window_size=window_size,overlap=overlap,target_bytes=union_size(spans))
        # Relocation does not change plan identity; source path is routing, not evidence.
        identity={k:v for k,v in values.items() if k!='path'}
        pid=digest(json.dumps(identity,sort_keys=True).encode())
        with self.connect() as c:
            c.execute('INSERT OR IGNORE INTO plans VALUES(?,?,?,?,?,?,?,?,?)',
                (pid,work_id,str(path),source_sha,values['zones_sha'],profile,window_size,overlap,values['target_bytes']))
            c.execute('UPDATE plans SET path=? WHERE id=?',(str(path),pid))
            c.executemany('INSERT OR IGNORE INTO jobs(plan_id,start,end) VALUES(?,?,?)',[(pid,a,b) for a,b in windows])
        return pid

    def claim(self,pid,lease_seconds=900,max_attempts=3,now=None):
        if lease_seconds<=0 or max_attempts<1: raise ValueError('invalid_limits')
        now=time.time() if now is None else now
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            expired=c.execute("SELECT id FROM jobs WHERE plan_id=? AND state='running' AND lease_until<=?",(pid,now)).fetchall()
            for row in expired:
                c.execute("UPDATE jobs SET state='error',error='lease_expired',token=NULL WHERE id=?",(row['id'],))
                c.execute('INSERT INTO events(job_id,at,kind,detail) VALUES(?,?,?,?)',(row['id'],now,'lease_expired','retry bounded'))
            row=c.execute("SELECT * FROM jobs WHERE plan_id=? AND state IN ('pending','error') AND attempts<? ORDER BY start,id LIMIT 1",(pid,max_attempts)).fetchone()
            if row is None: return None
            token=uuid.uuid4().hex
            c.execute("UPDATE jobs SET state='running',attempts=attempts+1,token=?,lease_until=? WHERE id=?",(token,now+lease_seconds,row['id']))
            c.execute('INSERT INTO events(job_id,at,kind,detail) VALUES(?,?,?,?)',(row['id'],now,'claimed',token))
            return dict(row,token=token,lease_until=now+lease_seconds)

    def fragment(self,job):
        with self.connect() as c: plan=dict(c.execute('SELECT * FROM plans WHERE id=?',(job['plan_id'],)).fetchone())
        data=Path(plan['path']).read_bytes()
        if digest(data)!=plan['source_sha'] or digest(Path(plan['path']).with_name('zones.json').read_bytes())!=plan['zones_sha']:
            raise ValueError('source_or_zones_drift')
        return data[job['start']:job['end']].decode('utf-8')

    def finish(self,job,result=None,error=None,now=None):
        now=time.time() if now is None else now
        if error is None and (not isinstance(result,list) or any(not isinstance(x,str) or not x.strip() for x in result)):
            raise ValueError('invalid_candidate_result')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM jobs WHERE id=?',(job['id'],)).fetchone()
            if not row or row['state']!='running' or row['token']!=job['token'] or row['lease_until']<=now:
                raise ValueError('stale_lease')
            state='error' if error is not None else 'done'
            c.execute('UPDATE jobs SET state=?,result_json=?,error=?,token=NULL,lease_until=NULL WHERE id=?',
                (state,json.dumps(result,ensure_ascii=False) if error is None else None,str(error) if error is not None else None,job['id']))
            c.execute('INSERT INTO events(job_id,at,kind,detail) VALUES(?,?,?,?)',
                (job['id'],now,state,str(error) if error is not None else 'candidates durably stored'))

    def status(self,pid):
        with self.connect() as c:
            plan=c.execute('SELECT * FROM plans WHERE id=?',(pid,)).fetchone()
            if plan is None: raise ValueError('unknown_plan')
            jobs=[dict(r) for r in c.execute('SELECT * FROM jobs WHERE plan_id=?',(pid,))]
        covered=union_size([(r['start'],r['end']) for r in jobs if r['state']=='done'])
        counts={s:sum(r['state']==s for r in jobs) for s in ['pending','running','done','error']}
        return dict(plan_id=pid,work_id=plan['work_id'],states=counts,total_jobs=len(jobs),
                    completed_bytes=covered,target_bytes=plan['target_bytes'],
                    coverage=covered/plan['target_bytes'],extraction_complete=counts['done']==len(jobs))

    def run(self,pid,client,work_title='',author_name='',max_windows=5):
        if not isinstance(max_windows,int) or max_windows<1: raise ValueError('invalid_budget')
        completed=0
        for _ in range(max_windows):
            job=self.claim(pid)
            if job is None: break
            try:
                text=self.fragment(job)
                candidates=client.propose_candidates(text,work_title,author_name)
                # Check artifact again after the external call, before granting coverage.
                self.fragment(job)
                self.finish(job,result=candidates)
                completed+=1
            except Exception as exc:
                try: self.finish(job,error=str(exc))
                except ValueError: pass  # A stale worker must never overwrite its successor.
                return dict(status='error',error=str(exc),completed_this_run=completed,progress=self.status(pid))
        return dict(status='extraction_batch_complete',completed_this_run=completed,progress=self.status(pid))
