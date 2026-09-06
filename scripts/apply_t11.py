"""
Script to apply T11: Drop first_attestation_year from terms and create earliest_attestation VIEW.
"""

import sqlite3

def main():
    conn = sqlite3.connect("data/scifi_lexicon.db")
    with conn:
        # Check SQLite version
        ver = conn.execute("SELECT sqlite_version()").fetchone()[0]
        print("SQLite version:", ver)

        # Check if first_attestation_year exists
        cols = [c[1] for c in conn.execute("PRAGMA table_info(terms)").fetchall()]
        if "first_attestation_year" in cols:
            try:
                conn.execute("ALTER TABLE terms DROP COLUMN first_attestation_year")
                print("Column first_attestation_year dropped via ALTER TABLE.")
            except Exception as e:
                print("ALTER TABLE DROP COLUMN failed, recreating table:", e)
                # Fallback table recreation
                cols_without = [c for c in cols if c != "first_attestation_year"]
                cols_str = ", ".join(cols_without)
                conn.execute(f"CREATE TABLE terms_backup AS SELECT {cols_str} FROM terms")
                conn.execute("DROP TABLE terms")
                conn.execute(f"CREATE TABLE terms AS SELECT * FROM terms_backup")
                conn.execute("DROP TABLE terms_backup")
                print("Table terms recreated without first_attestation_year.")

        # Create VIEW earliest_attestation
        conn.execute("DROP VIEW IF EXISTS earliest_attestation")
        conn.execute("""
            CREATE VIEW earliest_attestation AS
            SELECT term_orig,
                   MIN(year) AS earliest_year,
                   COUNT(*)  AS witness_count
            FROM attestations
            WHERE register='attested' AND zone='body' AND verified_at_utc IS NOT NULL
            GROUP BY term_orig
        """)
        print("VIEW earliest_attestation created.")

    conn.close()
    print("T11 applied successfully.")

if __name__ == "__main__":
    main()
