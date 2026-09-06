"""Plan all available corpus texts or inspect extraction progress, without LLM calls."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.corpus.queue import CorpusQueue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['plan', 'status', 'run'])
    parser.add_argument('--queue', type=Path, required=True)
    parser.add_argument('--profile', default='extraction-v1-unassigned-model')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--work-id', type=int)
    parser.add_argument('--model')
    parser.add_argument('--max-windows', type=int, default=5)
    args = parser.parse_args()
    queue = CorpusQueue(args.queue)
    if args.mode == 'run':
        if not args.work_id or not args.model or args.max_windows < 1:
            parser.error('run requires --work-id, --model and positive --max-windows')
        import hashlib
        import requests
        from modules.autoresearch.llm_client import LocalLLMClient
        client = LocalLLMClient(args.model)
        response = requests.get(client.base_url+'/api/tags', timeout=3)
        response.raise_for_status()
        matches = [m for m in response.json()['models'] if m['name'] == args.model]
        if len(matches) != 1 or not matches[0].get('digest'):
            raise ValueError('exact_local_model_digest_required')
        model_digest = matches[0]['digest']
        # Ollama generation uses the tag; guard its digest before and after each call.
        class PinnedClient:
            def propose_candidates(self, *values):
                def check():
                    tags = requests.get(client.base_url+'/api/tags',timeout=3)
                    tags.raise_for_status()
                    current = [m for m in tags.json()['models'] if m['name']==args.model]
                    if len(current)!=1 or current[0].get('digest')!=model_digest:
                        raise ValueError('model_digest_drift')
                check()
                result = client.propose_candidates(*values)
                check()
                return result
        profile = json.dumps(dict(model_digest=model_digest,
            client_sha256=hashlib.sha256((ROOT/'modules/autoresearch/llm_client.py').read_bytes()).hexdigest()), sort_keys=True)
        conn = sqlite3.connect((ROOT/'data/scifi_lexicon.db').as_uri()+'?mode=ro', uri=True)
        try:
            row = conn.execute('SELECT w.text_path,w.title_orig,a.name_orig FROM works w JOIN authors a ON a.id=w.author_id WHERE w.id=?', (args.work_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            raise ValueError('unknown_work')
        pid = queue.prepare(args.work_id,row[0],profile)
        result = queue.run(pid,PinnedClient(),row[1],row[2],args.max_windows)
        if args.report:
            with args.report.open('x',encoding='utf-8') as stream:
                json.dump(result,stream,ensure_ascii=False,indent=2)
        print(json.dumps(result,ensure_ascii=False))
        return 2 if result['status']=='error' else 0
    results, rejected = [], []
    if args.mode == 'plan':
        conn = sqlite3.connect((ROOT/'data/scifi_lexicon.db').as_uri()+'?mode=ro', uri=True)
        try:
            works = conn.execute('SELECT id,text_path FROM works WHERE has_full_text=1 ORDER BY cult_score DESC,id').fetchall()
        finally:
            conn.close()
        for work_id, path in works:
            try:
                pid = queue.prepare(work_id, path, args.profile)
                results.append(queue.status(pid))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                rejected.append(dict(work_id=work_id,error=str(exc)))
    else:
        with queue.connect() as conn:
            ids = [r[0] for r in conn.execute('SELECT id FROM plans ORDER BY work_id,id')]
        results = [queue.status(pid) for pid in ids]
    report = dict(scope='extraction_only_not_scientific_validation', plans=results, rejected=rejected)
    if args.report:
        with args.report.open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps(dict(plans=len(results),jobs=sum(r['total_jobs'] for r in results),
        target_bytes=sum(r['target_bytes'] for r in results),completed_bytes=sum(r['completed_bytes'] for r in results),
        rejected=rejected),ensure_ascii=False))
    return 2 if rejected else 0


if __name__ == '__main__':
    sys.exit(main())
