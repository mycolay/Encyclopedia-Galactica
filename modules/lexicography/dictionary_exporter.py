"""Evidence-first research export; never promotes proposals to verified articles."""
import hashlib
import json
import sqlite3
from pathlib import Path

from modules.corpus.witness import find_occurrences

DEFAULT_OUTPUT_MD = Path(__file__).resolve().parents[2] / 'docs' / 'SCI_FI_LEXICON.md'


def check_quote(record, path):
    """Independently check bytes, lexical match and hash-bound whole-span zone."""
    try:
        data = Path(path).read_bytes()
        start, size = record['byte_start'], record['byte_len']
        if not isinstance(start, int) or not isinstance(size, int) or start < 0 or size <= 0:
            return None, 'invalid_coordinates'
        if start + size > len(data):
            return None, 'short_read'
        if hashlib.sha256(data).hexdigest() != record['artifact_sha256']:
            return None, 'artifact_drift'
        window = data[start:start + size]
        if hashlib.sha256(window).hexdigest() != record['window_sha256']:
            return None, 'window_mismatch'
        quote = window.decode('utf-8')
        if not find_occurrences(window, record['term_orig']):
            return None, 'term_absent'
        zones = json.loads(Path(path).with_name('zones.json').read_text(encoding='utf-8'))
        if zones.get('source_sha256') != record['artifact_sha256']:
            return None, 'zone_hash_unbound'
        if record.get('zone') != 'body' or not any(
            z.get('kind') == 'body' and z['byte_start'] <= start
            and start + size <= z['byte_end'] for z in zones['zones']
        ):
            return None, 'outside_body'
        return quote, 'byte_verified_zone_map_checked'
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return None, 'unavailable_or_invalid_' + type(exc).__name__


class DictionaryExporter:
    def __init__(self, db, output_path=None):
        self.db = db
        self.output_path = Path(output_path or DEFAULT_OUTPUT_MD)

    def build_snapshot(self):
        # A separate read-only transaction: no init_db, migration or source mutation.
        uri = Path(self.db.db_path).resolve().as_uri() + '?mode=ro'
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('BEGIN')
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            works = {r['id']: dict(r) for r in conn.execute(
                'SELECT w.*, a.name_orig author_name FROM works w LEFT JOIN authors a ON a.id=w.author_id')}
            cards = {}

            def card(term, work_id):
                key = (term.casefold().strip(), work_id)
                if key not in cards:
                    w = works.get(work_id, {})
                    cards[key] = dict(term=term, work_id=work_id,
                        title=w.get('title_orig'), author=w.get('author_name'),
                        work_year=w.get('year'), definition=None, traditional=None,
                        attestations=[], proposals=[], external=[])
                return cards[key]

            for row in conn.execute('SELECT * FROM terms ORDER BY id'):
                c = card(row['term_orig'], row['work_id'])
                c['definition'] = row['scientific_definition']
                c['traditional'] = row['ukr_traditional']
            if 'attestations' in tables:
                for row in conn.execute('SELECT * FROM attestations ORDER BY id'):
                    r = dict(row)
                    c = card(r['term_orig'], r['work_id'])
                    if r['register'] == 'attested':
                        path = works.get(r['work_id'], {}).get('text_path')
                        quote, status = check_quote(r, path)
                        c['attestations'].append(dict(id=r['id'], year=r['year'],
                            quote=quote, check=status, path=path,
                            byte_start=r['byte_start'], byte_len=r['byte_len'],
                            artifact_sha256=r['artifact_sha256']))
                    elif r['register'] == 'proposed':
                        c['proposals'].append(dict(id=r['id'], variant=r['proposed_ukr_term'],
                            rationale=r.get('derivation_model'), note=r.get('stylistic_note'),
                            derivation_type=r.get('derivation_type'),
                            status='proposed_not_editorially_reviewed'))
                    elif r['register'] == 'external':
                        c['external'].append(dict(id=r['id'], authority=r['authority'],
                            url=r['authority_url'], status='external_not_rechecked'))
            ordered = sorted(cards.values(), key=lambda c: (c['term'].casefold(), c['work_id'] or -1))
            for c in ordered:
                years = [a['year'] for a in c['attestations'] if a['quote'] is not None and a['year'] is not None]
                c['earliest_in_work_corpus'] = min(years) if years else None
            return dict(schema_version='cosmoslov.research_cards.v1',
                status='research_draft', cards=ordered,
                counts=dict(cards=len(ordered), attestations=sum(len(c['attestations']) for c in ordered),
                    byte_verified=sum(a['quote'] is not None for c in ordered for a in c['attestations']),
                    proposals=sum(len(c['proposals']) for c in ordered)))
        finally:
            conn.close()

    def export_markdown(self):
        snapshot = self.build_snapshot()
        lines = ['# Космослов — дослідницькі картки', '',
            'Статус: дослідницька чернетка; редакторська й наукова перевірка статей не завершена.', '',
            'Картка описує термін у конкретному творі. Однакова назва ще не означає однакове поняття.', '',
            'Цитати перевірено за байтами та прив’язаною до хешу картою зон. Це не незалежна текстологічна перевірка самих меж зон.', '',
            'Дати походять із метаданих засвідчень; історична першість і бібліографічна точність дат потребують окремої перевірки.', '',
            'Статистика: ' + json.dumps(snapshot['counts'], ensure_ascii=False), '']
        for c in snapshot['cards']:
            lines += ['## ' + c['term'], '',
                f"Твір: {c['title'] or 'не встановлено'}. Автор: {c['author'] or 'не встановлено'}.", '']
            if c['definition']:
                lines += ['Визначення з попередніх даних — потребує редакторської перевірки:', c['definition'], '']
            if c['traditional']:
                lines += ['Український відповідник із попередніх даних; видання й перекладача не підтверджено:', c['traditional'], '']
            if c['earliest_in_work_corpus'] is not None:
                lines += [f"Найраніша дата серед перевірених записів цього твору в корпусі: {c['earliest_in_work_corpus']}.", '']
            for a in c['attestations']:
                lines += [f"Засвідчення #{a['id']}: {a['check']}.", '']
                if a['quote'] is not None:
                    # JSON preserves exact quote whitespace; Markdown trims line ends.
                    lines += [('> ' + line).rstrip() for line in a['quote'].splitlines()]
                    lines += ['', f"Артефакт: `{a['path']}`; байти {a['byte_start']}+{a['byte_len']}; SHA-256 `{a['artifact_sha256']}`.", '']
            if not any(a['quote'] is not None for a in c['attestations']):
                lines += ['Перевіреної корпусної цитати для цієї картки немає.', '']
            for p in c['proposals']:
                lines += [f"### Українська пропозиція: {p['variant']}", '',
                    'Статус: авторська/модельна пропозиція, редакторськи не затверджена.', '']
                if p['rationale']:
                    lines += ['Записане обґрунтування (словникові посилання цим експортом повторно не перевірялися):', p['rationale'], '']
                if p['note']:
                    lines += [p['note'], '']
            for e in c['external']:
                lines += [f"Зовнішнє свідчення #{e['id']}: {e['authority']}; {e['url'] or 'URL відсутній'}; повторно не перевірено.", '']
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_bytes(('\n'.join(lines).rstrip() + '\n').encode('utf-8'))
        self.output_path.with_suffix('.json').write_bytes(
            (json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        return self.output_path
