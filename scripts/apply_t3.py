"""
Script to apply T3: Retro-receipts for 10 authentic Project Gutenberg texts.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import inspect
import hashlib
import requests
from datetime import datetime, timezone
from pathlib import Path

from core.db import DatabaseManager
from modules.corpus.manager import CorpusManager
from modules.corpus.harvester import PublicDomainHarvester, PUBLIC_DOMAIN_SF_MASTERS
from modules.corpus.receipts import record_receipt

RIGHTS_BASIS_MAP = {
    "frankenstein": "Author died 1851, published 1818. Public Domain worldwide (pre-1929, life+70).",
    "the-time-machine": "Author died 1946, published 1895. Public Domain in US and UK (pre-1929, life+70).",
    "the-war-of-the-worlds": "Author died 1946, published 1898. Public Domain in US and UK (pre-1929, life+70).",
    "the-invisible-man": "Author died 1946, published 1897. Public Domain in US and UK (pre-1929, life+70).",
    "the-island-of-doctor-moreau": "Author died 1946, published 1896. Public Domain in US and UK (pre-1929, life+70).",
    "twenty-thousand-leagues-under-the-sea": "Author died 1905, published 1870. English translation pre-1923, Public Domain worldwide.",
    "from-the-earth-to-the-moon": "Author died 1905, published 1865. English translation pre-1923, Public Domain worldwide.",
    "journey-to-the-center-of-the-earth": "Author died 1905, published 1864. English translation 1877 (Malleson), Public Domain worldwide.",
    "flatland": "Author died 1926, published 1884. Public Domain worldwide (pre-1929, life+70).",
    "a-princess-of-mars": "Author died 1950, published 1912. Public Domain in US (pre-1929, life+70 in source country)."
}

def get_transform_sha() -> str:
    src = inspect.getsource(PublicDomainHarvester.clean_gutenberg_text)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()

def fetch_raw_with_url(g_id: int):
    urls = [
        f"https://www.gutenberg.org/files/{g_id}/{g_id}-0.txt",
        f"https://www.gutenberg.org/cache/epub/{g_id}/pg{g_id}.txt",
        f"https://raw.githubusercontent.com/the-best-book/gutenberg-mirror/main/{g_id}.txt"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutoSciFi-Harvester/2.0"}
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 1000:
                # Return raw binary content to calculate exact raw_sha256
                return resp.content, url, resp.status_code
        except Exception as e:
            continue
    return None, None, None

def main():
    db = DatabaseManager()
    corpus_mgr = CorpusManager()
    harvester = PublicDomainHarvester(corpus_mgr, db)
    transform_sha = get_transform_sha()

    print(f"Applying T3 for {len(PUBLIC_DOMAIN_SF_MASTERS)} authentic works...")
    verified_count = 0

    for spec in PUBLIC_DOMAIN_SF_MASTERS:
        slug = spec["slug"]
        g_id = spec["gutenberg_id"]
        author_slug = spec["author_slug"]
        print(f"\nProcessing {slug} (Gutenberg ID: {g_id})...")

        raw_bytes, source_url, http_status = fetch_raw_with_url(g_id)
        if not raw_bytes:
            print(f"ERROR: Failed to download Gutenberg ID {g_id} for {slug}")
            continue

        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        raw_size = len(raw_bytes)

        # Decode for cleaning
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = raw_bytes.decode("latin-1")

        clean_text = harvester.clean_gutenberg_text(raw_text)
        # Ensure clean text is strictly LF bytes
        clean_bytes = clean_text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        clean_sha = hashlib.sha256(clean_bytes).hexdigest()
        clean_size = len(clean_bytes)

        # Check against on-disk file
        work_dir = corpus_mgr.get_work_dir(author_slug, slug)
        orig_file = work_dir / "original.txt"

        note = None
        if orig_file.exists():
            on_disk_bytes = open(orig_file, "rb").read()
            on_disk_sha = hashlib.sha256(on_disk_bytes).hexdigest()
            if on_disk_sha != clean_sha:
                note = "clean_sha mismatch with on-disk file; on-disk replaced from source"
                print(f"Notice: on-disk SHA mismatch for {slug}. Replacing on-disk file.")
                # Re-package
                corpus_mgr.package_llm_ready_work(
                    author_slug=author_slug,
                    work_slug=slug,
                    text=clean_text,
                    metadata={
                        "title": spec["title_orig"],
                        "title_ukr": spec["title_ukr"],
                        "author_name": spec["author_name_orig"],
                        "year": spec["year"],
                        "original_lang": spec["original_lang"]
                    }
                )
            else:
                print(f"On-disk SHA matches clean download for {slug}.")
        else:
            print(f"File not found on disk for {slug}, packaging from clean download...")
            corpus_mgr.package_llm_ready_work(
                author_slug=author_slug,
                work_slug=slug,
                text=clean_text,
                metadata={
                    "title": spec["title_orig"],
                    "title_ukr": spec["title_ukr"],
                    "author_name": spec["author_name_orig"],
                    "year": spec["year"],
                    "original_lang": spec["original_lang"]
                }
            )

        # Record receipt
        is_trans = 1 if spec["original_lang"] != "en" else 0
        file_lang = "en"  # Gutenberg texts downloaded are in English

        record_receipt(
            work_slug=slug,
            edition_id=f"gutenberg:{g_id}",
            language=file_lang,
            is_translation=is_trans,
            rights="public_domain",
            rights_basis=RIGHTS_BASIS_MAP.get(slug, "Public Domain"),
            acquisition_class="verified",
            source_url=source_url,
            http_status=http_status,
            raw_sha256=raw_sha,
            raw_bytes=raw_size,
            clean_sha256=clean_sha,
            clean_bytes=clean_size,
            newline_policy="LF",
            transform_id="clean_gutenberg_text",
            transform_sha256=transform_sha,
            note=note
        )
        verified_count += 1
        print(f"Receipt recorded for {slug}: raw_sha={raw_sha[:8]}..., clean_sha={clean_sha[:8]}...")

    print(f"\nT3 completed: {verified_count} receipts recorded.")

if __name__ == "__main__":
    main()
