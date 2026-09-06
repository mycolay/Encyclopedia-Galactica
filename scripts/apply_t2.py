import os
import hashlib
import sqlite3
import shutil
from datetime import datetime, timezone

def main():
    conn = sqlite3.connect('data/scifi_lexicon.db')
    now_utc = datetime.now(timezone.utc).isoformat()

    quarantine_items = [
        ('rur-rossums-universal-robots', 'cs', 'data/corpus/texts/karel-capek/rur-rossums-universal-robots/original.txt', 'LLM-generated pastiche, not authentic. Quarantined 2026-09-06. Cyrillic U+043A/U+0430 inside Czech word člověка.'),
        ('foundation', 'en', 'data/corpus/texts/isaac-asimov/foundation/original.txt', 'LLM-generated pastiche, not authentic. Quarantined 2026-09-06.'),
        ('dune', 'en', 'data/corpus/texts/frank-herbert/dune/original.txt', 'LLM-generated pastiche, not authentic. Quarantined 2026-09-06.'),
        ('rocannons-world', 'en', 'data/corpus/texts/ursula-k-le-guin/rocannons-world/original.txt', 'LLM-generated pastiche, not authentic. Quarantined 2026-09-06.'),
        ('the-dispossessed', 'en', 'data/corpus/texts/ursula-k-le-guin/the-dispossessed/original.txt', 'LLM-generated pastiche, not authentic. Quarantined 2026-09-06.'),
        ('neuromancer', 'en', 'data/corpus/texts/william-gibson/neuromancer/original.txt', 'LLM-generated pastiche, not authentic. Quarantined 2026-09-06.'),
        ('test-work', 'en', 'data/corpus/texts/test-author/test-work/original.txt', 'LLM-generated pastiche, not authentic. Quarantined 2026-09-06.')
    ]

    for slug, lang, path, note in quarantine_items:
        if os.path.exists(path):
            data = open(path, 'rb').read()
            sha = hashlib.sha256(data).hexdigest()
            size = len(data)
            quarantine_path = path.replace('original.txt', 'original.QUARANTINE.txt')
            os.rename(path, quarantine_path)
            print(f'Renamed {path} -> {quarantine_path}')
        else:
            q_path = path.replace('original.txt', 'original.QUARANTINE.txt')
            if os.path.exists(q_path):
                data = open(q_path, 'rb').read()
                sha = hashlib.sha256(data).hexdigest()
                size = len(data)
            else:
                sha, size = None, None

        conn.execute('''
            INSERT OR REPLACE INTO acquisition_receipts (
                work_slug, edition_id, language, is_translation, fetched_at_utc,
                raw_sha256, raw_bytes, rights, acquisition_class, note
            ) VALUES (?, ?, ?, 0, ?, ?, ?, 'unknown', 'synthetic', ?)
        ''', (slug, 'synthetic:quarantine', lang, now_utc, sha, size, note))

    # Update works table
    conn.execute('''
        UPDATE works SET has_full_text = 0, research_status = 'quarantined'
        WHERE slug IN ('rur-rossums-universal-robots', 'foundation', 'dune', 'rocannons-world', 'the-dispossessed', 'neuromancer', 'test-work')
    ''')

    # Delete The First Starship from works
    conn.execute("DELETE FROM works WHERE title_orig LIKE '%First Starship%'")

    # Clean First Starship from disk if present
    starship_dir = 'K:/scifi_library/authors/arthur-pioneer'
    if os.path.exists(starship_dir):
        shutil.rmtree(starship_dir, ignore_errors=True)
        print('Removed trash dir:', starship_dir)

    conn.commit()
    conn.close()
    print('T2 applied successfully.')

if __name__ == '__main__':
    main()
