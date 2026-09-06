"""
Script to apply T4: Truly recover R.U.R. with both authentic Czech original (13083) and English translation (59112).
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

    print("=== Processing R.U.R. (T4) ===")

    # 1. Fetch Czech Original: 13083
    raw_cs, url_cs, status_cs = fetch_gutenberg_raw(13083)
    if not raw_cs:
        raise RuntimeError("Could not fetch Gutenberg 13083 (Czech)")

    raw_cs_sha = hashlib.sha256(raw_cs).hexdigest()
    text_cs = harvester.clean_gutenberg_text(raw_cs.decode("utf-8", errors="replace"))
    clean_cs_bytes = text_cs.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    clean_cs_sha = hashlib.sha256(clean_cs_bytes).hexdigest()

    # Package Czech Original on NAS
    pkg_cs = corpus_mgr.package_llm_ready_work(
        author_slug="karel-capek",
        work_slug="rur-rossums-universal-robots",
        text=text_cs,
        metadata={
            "title": "R.U.R. (Rossumovi Univerzální Roboti)",
            "title_ukr": "Р.У.Р. (Россумові універсальні роботи)",
            "author_name": "Karel Čapek",
            "year": 1920,
            "original_lang": "cs"
        }
    )

    # 2. Fetch English Translation: 59112
    raw_en, url_en, status_en = fetch_gutenberg_raw(59112)
    if not raw_en:
        raise RuntimeError("Could not fetch Gutenberg 59112 (English)")

    raw_en_sha = hashlib.sha256(raw_en).hexdigest()
    text_en = harvester.clean_gutenberg_text(raw_en.decode("utf-8", errors="replace"))
    clean_en_bytes = text_en.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    clean_en_sha = hashlib.sha256(clean_en_bytes).hexdigest()

    # Package English Translation on NAS as well
    pkg_en = corpus_mgr.package_llm_ready_work(
        author_slug="karel-capek",
        work_slug="rur-rossums-universal-robots-en",
        text=text_en,
        metadata={
            "title": "R.U.R. (Rossum's Universal Robots) - English Translation",
            "title_ukr": "Р.У.Р. (англійський переклад Селвера та Плейфейра)",
            "author_name": "Karel Čapek",
            "year": 1923,
            "original_lang": "en"
        }
    )

    # Also save translation file inside the primary work dir for reference
    trans_path = Path(pkg_cs["work_dir"]) / "translation_en.txt"
    with open(trans_path, "wb") as f:
        f.write(clean_en_bytes)

    # 3. Record receipts
    # Receipt 1: Czech Original
    record_receipt(
        work_slug="rur-rossums-universal-robots",
        edition_id="gutenberg:13083",
        language="cs",
        is_translation=0,
        rights="public_domain",
        rights_basis="Author died 1938, published 1920 (Aventinum). Public Domain in Czechia (life+70) and US (pre-1929).",
        acquisition_class="verified",
        source_url=url_cs,
        http_status=status_cs,
        raw_sha256=raw_cs_sha,
        raw_bytes=len(raw_cs),
        clean_sha256=clean_cs_sha,
        clean_bytes=len(clean_cs_bytes),
        newline_policy="LF",
        transform_id="clean_gutenberg_text",
        transform_sha256=transform_sha,
        note="Authentic Czech original text of R.U.R. acquired to replace synthetic quarantine."
    )
    print("Recorded receipt for Gutenberg 13083 (cs, authentic original)")

    # Receipt 2: English Translation
    record_receipt(
        work_slug="rur-rossums-universal-robots",
        edition_id="gutenberg:59112",
        language="en",
        is_translation=1,
        rights="public_domain",
        rights_basis="English translation by Paul Selver & Nigel Playfair published 1923 (Doubleday, Page & Co). Public Domain in US (pre-1929).",
        acquisition_class="verified",
        source_url=url_en,
        http_status=status_en,
        raw_sha256=raw_en_sha,
        raw_bytes=len(raw_en),
        clean_sha256=clean_en_sha,
        clean_bytes=len(clean_en_bytes),
        newline_policy="LF",
        transform_id="clean_gutenberg_text",
        transform_sha256=transform_sha,
        note="English translation edition for cross-lingual attestation."
    )
    print("Recorded receipt for Gutenberg 59112 (en, translation)")

    # 4. Update works table with authentic full text path
    conn = sqlite3.connect("data/scifi_lexicon.db")
    with conn:
        conn.execute("""
            UPDATE works
            SET has_full_text = 1,
                research_status = 'verified',
                text_path = ?
            WHERE slug = 'rur-rossums-universal-robots'
        """, (pkg_cs["full_text_path"],))
    conn.close()

    print("R.U.R. restored in works table with verified authentic Czech text.")

if __name__ == "__main__":
    main()
