"""
Script to apply T8: Create attestations table with CHECK constraints for 3 registers.
"""

import sqlite3

SCHEMA_T8_SQL = """
CREATE TABLE IF NOT EXISTS attestations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  term_id INTEGER REFERENCES terms(id) ON DELETE CASCADE,
  term_orig TEXT NOT NULL,
  work_id INTEGER,
  year INTEGER,
  register TEXT NOT NULL CHECK (register IN ('attested','external','proposed')),
  zone TEXT,
  matched_form TEXT,

  cts_urn TEXT,
  artifact_sha256 TEXT,
  byte_start INTEGER,
  byte_len INTEGER,
  window_sha256 TEXT,

  authority TEXT,
  authority_url TEXT,
  authority_snapshot_sha256 TEXT,
  retrieved_at_utc TEXT,

  proposed_ukr_term TEXT,
  grinchenko_root TEXT,
  derivation_model TEXT,
  stylistic_note TEXT,
  root_attested_in_grinchenko INTEGER DEFAULT 0,

  verified_at_utc TEXT,
  verifier_version TEXT,
  proposed_by_model TEXT,

  CHECK (
    (register='attested' AND cts_urn IS NOT NULL AND artifact_sha256 IS NOT NULL
      AND byte_start IS NOT NULL AND byte_len IS NOT NULL AND window_sha256 IS NOT NULL)
    OR (register='external' AND authority IS NOT NULL AND authority_snapshot_sha256 IS NOT NULL)
    OR (register='proposed' AND cts_urn IS NULL AND artifact_sha256 IS NULL
      AND proposed_ukr_term IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_attestations_lookup
  ON attestations(term_orig, register, zone);
"""

def init_attestations_table(db_path: str = "data/scifi_lexicon.db"):
    conn = sqlite3.connect(db_path)
    with conn:
        conn.executescript(SCHEMA_T8_SQL)
    conn.close()

if __name__ == "__main__":
    init_attestations_table()
    print("Table attestations created successfully.")
