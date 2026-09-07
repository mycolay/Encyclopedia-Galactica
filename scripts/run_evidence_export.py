"""Run evidence export against an SQLite backup and record reproducibility hashes."""
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.lexicography.dictionary_exporter import DictionaryExporter


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = ROOT / '.benchmarks' / ('evidence-export-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'data' / 'scifi_lexicon.db'
    backup = run / 'snapshot.db'
    src = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    dst = sqlite3.connect(backup)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    exporter = DictionaryExporter(SimpleNamespace(db_path=backup), run / 'SCI_FI_LEXICON.md')
    exporter.export_markdown()
    payload = json.loads((run / 'SCI_FI_LEXICON.json').read_text(encoding='utf-8'))
    inputs = [Path(__file__), ROOT/'modules/lexicography/dictionary_exporter.py',
        ROOT/'modules/corpus/witness.py', ROOT/'tests/test_evidence_export.py', ROOT/'docs/ARTICLE_CONTRACT_V1.md']
    receipt = dict(status='research_export_not_scientific_validation',
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        python=sys.version, sqlite=sqlite3.sqlite_version,
        counts=payload['counts'], snapshot_sha256=digest(backup),
        executor_files={str(p.relative_to(ROOT)):digest(p) for p in inputs},
        outputs={p.name:digest(p) for p in [run/'SCI_FI_LEXICON.md',run/'SCI_FI_LEXICON.json']},
        rejected=[dict(term=c['term'],id=a['id'],reason=a['check'])
            for c in payload['cards'] for a in c['attestations'] if a['quote'] is None],
        limitation='Plain SHA-256 receipt, not an Exometric seal or externally anchored audit. Corpus source files must remain available for replay.')
    (run/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(run=str(run),counts=payload['counts'],rejected=receipt['rejected']),ensure_ascii=False))


if __name__ == '__main__':
    main()
