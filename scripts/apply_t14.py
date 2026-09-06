"""
Script to apply T14: Transition existing 5 terms to honest state (COSMOSLOV_TZ_EXECUTOR_V2).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import sqlite3
from datetime import datetime, timezone
from modules.corpus.witness import build_witness, verify_witness, find_occurrences
from modules.corpus.zones import get_zone_for_byte

def main():
    conn = sqlite3.connect("data/scifi_lexicon.db")
    now_utc = datetime.now(timezone.utc).isoformat()

    print("=== Applying T14: Transitioning 5 Terms to Honest State ===")

    # 1. Read existing terms
    terms = conn.execute("""
        SELECT id, term_orig, work_id, original_context, ukr_traditional, ukr_grinchenko_json, morphological_rationale
        FROM terms
    """).fetchall()

    for row in terms:
        t_id, term_orig, work_id, orig_context, ukr_trad, ukr_grin_json, morph_rationale = row
        print(f"\nProcessing term '{term_orig}' (ID: {t_id})...")

        proposals = []
        if ukr_grin_json:
            try:
                proposals = json.loads(ukr_grin_json)
            except Exception:
                pass

        if not proposals and ukr_trad:
            proposals = [{"variant": ukr_trad, "morphemes": "traditional loan", "semantic_nuance": "традиційне запозичення"}]

        for p in proposals:
            variant = p.get("variant", "").strip()
            if not variant:
                continue

            conn.execute("""
                INSERT INTO attestations (
                    term_id, term_orig, work_id, year, register,
                    proposed_ukr_term, grinchenko_root, derivation_model,
                    stylistic_note, root_attested_in_grinchenko,
                    verified_at_utc, verifier_version, proposed_by_model
                ) VALUES (?, ?, ?, ?, 'proposed', ?, ?, ?, ?, 0, ?, 'v2.0', 'qwen3.5:27b')
            """, (
                t_id,
                term_orig,
                work_id,
                None,
                variant,
                p.get("morphemes", "").split()[0] if p.get("morphemes") else None,
                p.get("grinchenko_model") or p.get("morphemes"),
                p.get("semantic_nuance") or morph_rationale,
                now_utc
            ))
            print(f"  Recorded proposal: '{variant}' (register=proposed)")

    # 2. Build authentic witness for 'robot' from Czech R.U.R.
    rur_path = "K:/scifi_library/authors/karel-capek/rur-rossums-universal-robots/full_text.md"
    zones_path = "K:/scifi_library/authors/karel-capek/rur-rossums-universal-robots/zones.json"

    if os.path.exists(rur_path) and os.path.exists(zones_path):
        with open(zones_path, "r", encoding="utf-8") as f:
            z_data = json.load(f)

        data = open(rur_path, "rb").read()
        occs = find_occurrences(data, "robot")

        for idx in range(len(occs)):
            w = build_witness(rur_path, "robot", occurrence_index=idx)
            zone = get_zone_for_byte(z_data, w["byte_start"])
            if zone == "body":
                status, reason, text = verify_witness(w, rur_path, "robot")
                if status == "ACCEPT":
                    conn.execute("""
                        INSERT INTO attestations (
                            term_id, term_orig, work_id, year, register,
                            zone, matched_form, cts_urn, artifact_sha256,
                            byte_start, byte_len, window_sha256,
                            verified_at_utc, verifier_version
                        ) VALUES (
                            1, 'robot', 1, 1920, 'attested',
                            'body', ?, 'urn:cts:scifi:capek.rur:1920', ?,
                            ?, ?, ?, ?, 'witness.v2'
                        )
                    """, (
                        w["matched_form"],
                        w["artifact_sha256"],
                        w["byte_start"],
                        w["byte_len"],
                        w["window_sha256"],
                        now_utc
                    ))
                    print(f"\nBuilt verified authentic witness for 'robot': offset={w['byte_start']}, form='{w['matched_form']}'")
                    break

    # 3. Migrate terms table to make original_context and ukr_translated_context NULLABLE
    conn.execute("DROP VIEW IF EXISTS earliest_attestation")
    conn.execute("""
        CREATE TABLE terms_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term_orig TEXT NOT NULL,
            ipa TEXT,
            work_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            original_context TEXT,
            context_source_locator TEXT,
            concept_category TEXT NOT NULL,
            scientific_definition TEXT NOT NULL,
            ukr_traditional TEXT,
            ukr_grinchenko_json TEXT DEFAULT '[]',
            morphological_rationale TEXT,
            ukr_translated_context TEXT,
            verification_score REAL DEFAULT 0.0,
            status TEXT DEFAULT 'verified',
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        INSERT INTO terms_new (
            id, term_orig, ipa, work_id, author_id,
            original_context, context_source_locator, concept_category,
            scientific_definition, ukr_traditional, ukr_grinchenko_json,
            morphological_rationale, ukr_translated_context, verification_score, status
        )
        SELECT 
            id, term_orig, ipa, work_id, author_id,
            NULL, NULL, concept_category,
            scientific_definition, ukr_traditional, ukr_grinchenko_json,
            morphological_rationale, NULL, verification_score, status
        FROM terms
    """)

    conn.execute("DROP TABLE terms")
    conn.execute("ALTER TABLE terms_new RENAME TO terms")

    # Recreate earliest_attestation VIEW
    conn.execute("""
        CREATE VIEW earliest_attestation AS
        SELECT term_orig,
               MIN(year) AS earliest_year,
               COUNT(*)  AS witness_count
        FROM attestations
        WHERE register='attested' AND zone='body' AND verified_at_utc IS NOT NULL
        GROUP BY term_orig
    """)

    conn.commit()
    conn.close()
    print("\nTerms table successfully migrated: all fabricated quotes deleted (original_context=NULL).")
    print("T14 completed successfully.")

if __name__ == "__main__":
    main()
