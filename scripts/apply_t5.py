"""
Script to apply T5: Expand Public Domain Library with authentic masterworks and receipts.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import inspect
import hashlib
import sqlite3
import requests
from datetime import datetime, timezone
from pathlib import Path

from core.db import DatabaseManager
from modules.corpus.manager import CorpusManager
from modules.corpus.harvester import PublicDomainHarvester
from modules.corpus.receipts import record_receipt

VERIFIED_CANDIDATES = [
    {
        "slug": "the-first-men-in-the-moon",
        "title_orig": "The First Men in the Moon",
        "title_ukr": "Перші люди на Місяці",
        "author_slug": "h-g-wells",
        "author_name": "H.G. Wells",
        "author_name_ukr": "Герберт Веллс",
        "birth_year": 1866,
        "death_year": 1946,
        "country": "UK",
        "year": 1901,
        "gutenberg_id": 1013,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1946, published 1901. Public Domain in US (pre-1929) and UK (life+70)."
    },
    {
        "slug": "when-the-sleeper-wakes",
        "title_orig": "When the Sleeper Wakes (The Sleeper Awakes)",
        "title_ukr": "Коли сплячий прокидається",
        "author_slug": "h-g-wells",
        "author_name": "H.G. Wells",
        "author_name_ukr": "Герберт Веллс",
        "birth_year": 1866,
        "death_year": 1946,
        "country": "UK",
        "year": 1899,
        "gutenberg_id": 12163,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1946, published 1899 (revised 1910). Public Domain in US (pre-1929) and UK (life+70)."
    },
    {
        "slug": "around-the-moon",
        "title_orig": "All Around the Moon (Autour de la Lune)",
        "title_ukr": "Навколо Місяця",
        "author_slug": "jules-verne",
        "author_name": "Jules Verne",
        "author_name_ukr": "Жуль Верн",
        "birth_year": 1828,
        "death_year": 1905,
        "country": "France",
        "year": 1870,
        "gutenberg_id": 16457,
        "original_lang": "fr",
        "is_translation": 1,
        "rights_basis": "Author died 1905, published 1870. English translation pre-1923, Public Domain worldwide."
    },
    {
        "slug": "robur-the-conqueror",
        "title_orig": "Robur the Conqueror",
        "title_ukr": "Робур-Переможець",
        "author_slug": "jules-verne",
        "author_name": "Jules Verne",
        "author_name_ukr": "Жуль Верн",
        "birth_year": 1828,
        "death_year": 1905,
        "country": "France",
        "year": 1886,
        "gutenberg_id": 3808,
        "original_lang": "fr",
        "is_translation": 1,
        "rights_basis": "Author died 1905, published 1886. English translation pre-1923, Public Domain worldwide."
    },
    {
        "slug": "the-gods-of-mars",
        "title_orig": "The Gods of Mars",
        "title_ukr": "Боги Марса",
        "author_slug": "edgar-rice-burroughs",
        "author_name": "Edgar Rice Burroughs",
        "author_name_ukr": "Едгар Райс Берроуз",
        "birth_year": 1875,
        "death_year": 1950,
        "country": "USA",
        "year": 1913,
        "gutenberg_id": 64,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1950, published 1913. Public Domain in US (pre-1929)."
    },
    {
        "slug": "the-land-that-time-forgot",
        "title_orig": "The Land That Time Forgot",
        "title_ukr": "Земля, забута часом",
        "author_slug": "edgar-rice-burroughs",
        "author_name": "Edgar Rice Burroughs",
        "author_name_ukr": "Едгар Райс Берроуз",
        "birth_year": 1875,
        "death_year": 1950,
        "country": "USA",
        "year": 1918,
        "gutenberg_id": 551,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1950, published 1918. Public Domain in US (pre-1929)."
    },
    {
        "slug": "looking-backward",
        "title_orig": "Looking Backward: 2000 to 1887",
        "title_ukr": "Погляд назад: 2000–1887",
        "author_slug": "edward-bellamy",
        "author_name": "Edward Bellamy",
        "author_name_ukr": "Едвард Белламі",
        "birth_year": 1850,
        "death_year": 1898,
        "country": "USA",
        "year": 1888,
        "gutenberg_id": 624,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1898, published 1888. Public Domain worldwide (life+70, pre-1929)."
    },
    {
        "slug": "erewhon",
        "title_orig": "Erewhon; or, Over the Range",
        "title_ukr": "Еревон",
        "author_slug": "samuel-butler",
        "author_name": "Samuel Butler",
        "author_name_ukr": "Семюель Батлер",
        "birth_year": 1835,
        "death_year": 1902,
        "country": "UK",
        "year": 1872,
        "gutenberg_id": 1906,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1902, published 1872. Public Domain worldwide (life+70, pre-1929)."
    },
    {
        "slug": "the-coming-race",
        "title_orig": "The Coming Race",
        "title_ukr": "Грядуща раса",
        "author_slug": "edward-bulwer-lytton",
        "author_name": "Edward Bulwer-Lytton",
        "author_name_ukr": "Едвард Бульвер-Літтон",
        "birth_year": 1803,
        "death_year": 1873,
        "country": "UK",
        "year": 1871,
        "gutenberg_id": 1951,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1873, published 1871. Public Domain worldwide (life+70, pre-1929)."
    },
    {
        "slug": "herland",
        "title_orig": "Herland",
        "title_ukr": "Їїземля (Герланд)",
        "author_slug": "charlotte-perkins-gilman",
        "author_name": "Charlotte Perkins Gilman",
        "author_name_ukr": "Шарлотта Перкінс Гілман",
        "birth_year": 1860,
        "death_year": 1935,
        "country": "USA",
        "year": 1915,
        "gutenberg_id": 32,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1935, published 1915. Public Domain worldwide (pre-1929, life+70)."
    },
    {
        "slug": "the-blazing-world",
        "title_orig": "The Description of a New World, Called The Blazing-World",
        "title_ukr": "Палаючий світ",
        "author_slug": "margaret-cavendish",
        "author_name": "Margaret Cavendish",
        "author_name_ukr": "Маргарет Кавендіш",
        "birth_year": 1623,
        "death_year": 1673,
        "country": "UK",
        "year": 1666,
        "gutenberg_id": 51783,
        "original_lang": "en",
        "is_translation": 0,
        "rights_basis": "Author died 1673, published 1666. Public Domain worldwide."
    },
    {
        "slug": "micromegas",
        "title_orig": "Micromégas",
        "title_ukr": "Мікромегас",
        "author_slug": "voltaire",
        "author_name": "Voltaire",
        "author_name_ukr": "Вольтер",
        "birth_year": 1694,
        "death_year": 1778,
        "country": "France",
        "year": 1752,
        "gutenberg_id": 4649,
        "original_lang": "fr",
        "is_translation": 0,
        "rights_basis": "Author died 1778, published 1752 (original French). Public Domain worldwide."
    }
]

def get_or_create_author(conn, item):
    slug = item["author_slug"]
    cur = conn.execute("SELECT id FROM authors WHERE slug = ?", (slug,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute("""
        INSERT INTO authors (
            slug, name_orig, name_ukr, birth_year, death_year,
            country, primary_language, cult_tier, cult_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 92.0)
    """, (
        slug, item["author_name"], item["author_name_ukr"],
        item["birth_year"], item["death_year"], item["country"], item["original_lang"]
    ))
    return cur.lastrowid

def get_transform_sha():
    src = inspect.getsource(PublicDomainHarvester.clean_gutenberg_text)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()

def fetch_gutenberg_raw(g_id: int):
    urls = [
        f"https://www.gutenberg.org/cache/epub/{g_id}/pg{g_id}.txt",
        f"https://www.gutenberg.org/files/{g_id}/{g_id}-0.txt",
        f"https://raw.githubusercontent.com/the-best-book/gutenberg-mirror/main/{g_id}.txt"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutoSciFi-Harvester/2.0"}
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content, url, resp.status_code
        except Exception:
            continue
    return None, None, None

def main():
    db = DatabaseManager()
    corpus_mgr = CorpusManager()
    harvester = PublicDomainHarvester(corpus_mgr, db)
    transform_sha = get_transform_sha()
    conn = sqlite3.connect("data/scifi_lexicon.db")

    print(f"=== Applying T5: Expanding PD Library with {len(VERIFIED_CANDIDATES)} works ===")

    for item in VERIFIED_CANDIDATES:
        slug = item["slug"]
        gid = item["gutenberg_id"]
        print(f"\nProcessing {item['title_orig']} (GID {gid})...")

        raw_bytes, url, status = fetch_gutenberg_raw(gid)
        if not raw_bytes:
            print(f"ERROR: Could not fetch Gutenberg {gid} for {slug}")
            continue

        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        raw_size = len(raw_bytes)

        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = raw_bytes.decode("latin-1")

        clean_text = harvester.clean_gutenberg_text(raw_text)
        clean_bytes = clean_text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        clean_sha = hashlib.sha256(clean_bytes).hexdigest()
        clean_size = len(clean_bytes)

        # Package on NAS
        pkg = corpus_mgr.package_llm_ready_work(
            author_slug=item["author_slug"],
            work_slug=slug,
            text=clean_text,
            metadata={
                "title": item["title_orig"],
                "title_ukr": item["title_ukr"],
                "author_name": item["author_name"],
                "year": item["year"],
                "original_lang": item["original_lang"]
            }
        )

        file_lang = "fr" if slug == "micromegas" else "en"

        # Record receipt
        record_receipt(
            work_slug=slug,
            edition_id=f"gutenberg:{gid}",
            language=file_lang,
            is_translation=item["is_translation"],
            rights="public_domain",
            rights_basis=item["rights_basis"],
            acquisition_class="verified",
            source_url=url,
            http_status=status,
            raw_sha256=raw_sha,
            raw_bytes=raw_size,
            clean_sha256=clean_sha,
            clean_bytes=clean_size,
            newline_policy="LF",
            transform_id="clean_gutenberg_text",
            transform_sha256=transform_sha,
            note=f"Verified public domain acquisition from Project Gutenberg #{gid}."
        )

        # Ensure author exists in authors table
        author_id = get_or_create_author(conn, item)

        # Insert or update in works table
        conn.execute("""
            INSERT INTO works (
                slug, author_id, title_orig, title_ukr,
                year, original_lang, has_full_text, text_path,
                word_count, research_status
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 'verified')
            ON CONFLICT(slug) DO UPDATE SET
                author_id=excluded.author_id,
                title_orig=excluded.title_orig,
                title_ukr=excluded.title_ukr,
                year=excluded.year,
                original_lang=excluded.original_lang,
                has_full_text=1,
                text_path=excluded.text_path,
                word_count=excluded.word_count,
                research_status='verified'
        """, (
            slug, author_id, item["title_orig"], item["title_ukr"],
            item["year"], item["original_lang"], pkg["full_text_path"], pkg["word_count"]
        ))
        conn.commit()
        print(f"Recorded and packaged: {slug} (words: {pkg['word_count']})")

    # Handle the-machine-stops (E.M. Forster): absent due to UK copyright
    print("\nRecording receipt for the-machine-stops (absent due to UK Life+70)...")
    record_receipt(
        work_slug="the-machine-stops",
        edition_id="gutenberg:absent",
        language="en",
        is_translation=0,
        rights="copyright_ambiguous",
        rights_basis="Author E.M. Forster died 1970; UK life+70 in country of origin protected until 2041. Excluded from full text acquisition.",
        acquisition_class="absent",
        note="Full text intentionally NOT acquired due to UK life+70 copyright."
    )

    forster_id = get_or_create_author(conn, {
        "author_slug": "e-m-forster",
        "author_name": "E.M. Forster",
        "author_name_ukr": "Едвард Морган Форстер",
        "birth_year": 1879,
        "death_year": 1970,
        "country": "UK",
        "original_lang": "en"
    })

    conn.execute("""
        INSERT INTO works (
            slug, author_id, title_orig, title_ukr,
            year, original_lang, has_full_text, research_status
        ) VALUES (?, ?, ?, ?, ?, ?, 0, 'absent')
        ON CONFLICT(slug) DO UPDATE SET
            author_id=excluded.author_id,
            has_full_text=0,
            research_status='absent'
    """, (
        "the-machine-stops", forster_id, "The Machine Stops", "Машина зупиняється",
        1909, "en"
    ))
    conn.commit()
    conn.close()
    print("T5 completed successfully.")

if __name__ == "__main__":
    main()
