"""
Acquisition Receipts Module (Т1 - COSMOSLOV_TZ_EXECUTOR_V2)
Tracks cryptographic provenance, byte hashes, transformations, and copyright basis for all corpus items.
"""

import sqlite3
import datetime
from typing import Optional, Dict, Any
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS acquisition_receipts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_slug TEXT NOT NULL,
  edition_id TEXT NOT NULL,
  language TEXT NOT NULL,
  is_translation INTEGER NOT NULL DEFAULT 0,
  source_url TEXT,
  http_status INTEGER,
  fetched_at_utc TEXT NOT NULL,
  raw_sha256 TEXT,
  raw_bytes INTEGER,
  clean_sha256 TEXT,
  clean_bytes INTEGER,
  newline_policy TEXT DEFAULT 'LF',
  transform_id TEXT,
  transform_sha256 TEXT,
  rights TEXT NOT NULL,
  rights_basis TEXT,
  acquisition_class TEXT NOT NULL
    CHECK (acquisition_class IN ('verified','synthetic','unsourced','absent')),
  note TEXT,
  UNIQUE (work_slug, edition_id)
);
"""


def init_receipts_table(db_path: str = "data/scifi_lexicon.db") -> None:
    """Ensures the acquisition_receipts table exists with all required columns and constraints."""
    conn = sqlite3.connect(db_path)
    with conn:
        conn.executescript(SCHEMA_SQL)
    conn.close()


def record_receipt(
    work_slug: str,
    edition_id: str,
    language: str,
    is_translation: int,
    rights: str,
    acquisition_class: str,
    source_url: Optional[str] = None,
    http_status: Optional[int] = None,
    raw_sha256: Optional[str] = None,
    raw_bytes: Optional[int] = None,
    clean_sha256: Optional[str] = None,
    clean_bytes: Optional[int] = None,
    newline_policy: str = "LF",
    transform_id: Optional[str] = None,
    transform_sha256: Optional[str] = None,
    rights_basis: Optional[str] = None,
    note: Optional[str] = None,
    db_path: str = "data/scifi_lexicon.db",
) -> int:
    """Inserts or replaces an acquisition receipt in the database."""
    init_receipts_table(db_path)
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    sql = """
    INSERT INTO acquisition_receipts (
        work_slug, edition_id, language, is_translation, source_url,
        http_status, fetched_at_utc, raw_sha256, raw_bytes, clean_sha256,
        clean_bytes, newline_policy, transform_id, transform_sha256,
        rights, rights_basis, acquisition_class, note
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?
    )
    ON CONFLICT(work_slug, edition_id) DO UPDATE SET
        language=excluded.language,
        is_translation=excluded.is_translation,
        source_url=excluded.source_url,
        http_status=excluded.http_status,
        fetched_at_utc=excluded.fetched_at_utc,
        raw_sha256=excluded.raw_sha256,
        raw_bytes=excluded.raw_bytes,
        clean_sha256=excluded.clean_sha256,
        clean_bytes=excluded.clean_bytes,
        newline_policy=excluded.newline_policy,
        transform_id=excluded.transform_id,
        transform_sha256=excluded.transform_sha256,
        rights=excluded.rights,
        rights_basis=excluded.rights_basis,
        acquisition_class=excluded.acquisition_class,
        note=excluded.note
    """

    conn = sqlite3.connect(db_path)
    with conn:
        cur = conn.execute(
            sql,
            (
                work_slug,
                edition_id,
                language,
                is_translation,
                source_url,
                http_status,
                now_utc,
                raw_sha256,
                raw_bytes,
                clean_sha256,
                clean_bytes,
                newline_policy,
                transform_id,
                transform_sha256,
                rights,
                rights_basis,
                acquisition_class,
                note,
            ),
        )
        receipt_id = cur.lastrowid
    conn.close()
    return receipt_id


if __name__ == "__main__":
    init_receipts_table()
    print("acquisition_receipts table initialized.")
