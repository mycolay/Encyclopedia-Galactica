import hashlib
import json
import sqlite3
from types import SimpleNamespace

from modules.lexicography.dictionary_exporter import DictionaryExporter
from modules.corpus.witness import build_witness


def fixture_export(tmp_path, count=1):
    source = tmp_path / 'source.txt'
    source.write_text('Robot walks across the room.', encoding='utf-8')
    w = build_witness(str(source), 'Robot', pad=0)
    source.with_name('zones.json').write_text(json.dumps(dict(source_sha256=w['artifact_sha256'],
        zones=[dict(kind='body', byte_start=0, byte_end=source.stat().st_size)])), encoding='utf-8')
    db = tmp_path / 'test.db'
    with sqlite3.connect(db) as c:
        c.executescript('''
        CREATE TABLE authors(id INTEGER, name_orig TEXT);
        CREATE TABLE works(id INTEGER, author_id INTEGER, title_orig TEXT, year INTEGER, text_path TEXT);
        CREATE TABLE terms(id INTEGER, term_orig TEXT, work_id INTEGER, scientific_definition TEXT, ukr_traditional TEXT);
        CREATE TABLE attestations(id INTEGER, term_orig TEXT, work_id INTEGER, register TEXT, year INTEGER,
        zone TEXT, byte_start INTEGER, byte_len INTEGER, artifact_sha256 TEXT, window_sha256 TEXT,
        matched_form TEXT, proposed_ukr_term TEXT, derivation_model TEXT);
        INSERT INTO authors VALUES(1,'Author');
        ''')
        c.execute('INSERT INTO works VALUES(1,1,?,?,?)', ('Book',1900,str(source)))
        c.executemany('INSERT INTO terms VALUES(?,?,1,NULL,NULL)', [(i, 'term'+str(i)) for i in range(count)])
        c.execute('INSERT INTO attestations VALUES(1,?,1,?,1900,?,?,?,?,?,?,NULL,NULL)',
            ('Robot','attested','body',w['byte_start'],w['byte_len'],w['artifact_sha256'],w['window_sha256'],w['matched_form']))
        c.execute("INSERT INTO attestations(id,term_orig,work_id,register,proposed_ukr_term,derivation_model) VALUES(2,'Robot',1,'proposed','Робітник','NEW RATIONALE')")
    return DictionaryExporter(SimpleNamespace(db_path=db), tmp_path/'out.md'), source


def test_unlinked_witness_and_proposal_export_without_db_mutation(tmp_path):
    exporter, source = fixture_export(tmp_path)
    before = hashlib.sha256(exporter.db.db_path.read_bytes()).hexdigest()
    output = exporter.export_markdown().read_text(encoding='utf-8')
    assert 'Robot walks' in output
    assert 'NEW RATIONALE' in output
    assert 'None' not in output
    assert 'редакторськи не затверджена' in output
    assert hashlib.sha256(exporter.db.db_path.read_bytes()).hexdigest() == before


def test_tampered_source_never_publishes_quote(tmp_path):
    exporter, source = fixture_export(tmp_path)
    source.write_text('Robot forged quote'.ljust(source.stat().st_size), encoding='utf-8')
    output = exporter.export_markdown().read_text(encoding='utf-8')
    assert 'artifact_drift' in output
    assert 'forged quote' not in output


def test_wrong_term_cannot_pass_by_matched_form(tmp_path):
    exporter, source = fixture_export(tmp_path)
    with sqlite3.connect(exporter.db.db_path) as c:
        c.execute("UPDATE attestations SET term_orig='Ansible' WHERE id=1")
    assert exporter.build_snapshot()['counts']['byte_verified'] == 0


def test_zone_tamper_and_missing_map_fail_closed(tmp_path):
    exporter, source = fixture_export(tmp_path)
    zones = source.with_name('zones.json')
    data = json.loads(zones.read_text())
    data['zones'][0]['byte_start'] = 2
    zones.write_text(json.dumps(data))
    assert exporter.build_snapshot()['counts']['byte_verified'] == 0
    zones.unlink()
    assert exporter.build_snapshot()['counts']['byte_verified'] == 0


def test_no_thousand_card_limit(tmp_path):
    exporter, _ = fixture_export(tmp_path, count=1002)
    assert exporter.build_snapshot()['counts']['cards'] == 1003
