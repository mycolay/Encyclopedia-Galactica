"""
Script to apply T6: Record receipts for in-copyright works (intentionally NOT acquiring full text).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sqlite3
from datetime import datetime, timezone
from modules.corpus.receipts import record_receipt

IN_COPYRIGHT_WORKS = [
    {
        "slug": "dune",
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "lang": "en",
        "basis": "Published 1965, author Frank Herbert (1920-1986), still under copyright worldwide."
    },
    {
        "slug": "neuromancer",
        "title": "Neuromancer",
        "author": "William Gibson",
        "year": 1984,
        "lang": "en",
        "basis": "Published 1984, author William Gibson (living), still under copyright worldwide."
    },
    {
        "slug": "foundation",
        "title": "Foundation",
        "author": "Isaac Asimov",
        "year": 1951,
        "lang": "en",
        "basis": "Published 1951, author Isaac Asimov (1920-1992), still under copyright worldwide."
    },
    {
        "slug": "solaris",
        "title": "Solaris",
        "author": "Stanisław Lem",
        "year": 1961,
        "lang": "pl",
        "basis": "Published 1961, author Stanisław Lem (1921-2006), still under copyright worldwide."
    },
    {
        "slug": "hyperion",
        "title": "Hyperion",
        "author": "Dan Simmons",
        "year": 1989,
        "lang": "en",
        "basis": "Published 1989, author Dan Simmons (living), still under copyright worldwide."
    },
    {
        "slug": "ubik",
        "title": "Ubik",
        "author": "Philip K. Dick",
        "year": 1969,
        "lang": "en",
        "basis": "Published 1969, author Philip K. Dick (1928-1982), still under copyright worldwide."
    },
    {
        "slug": "2001-a-space-odyssey",
        "title": "2001: A Space Odyssey",
        "author": "Arthur C. Clarke",
        "year": 1968,
        "lang": "en",
        "basis": "Published 1968, author Arthur C. Clarke (1917-2008), still under copyright worldwide."
    },
    {
        "slug": "blindsight",
        "title": "Blindsight",
        "author": "Peter Watts",
        "year": 2006,
        "lang": "en",
        "basis": "Published 2006, author Peter Watts (living), creative commons / copyright reserved."
    },
    {
        "slug": "the-three-body-problem",
        "title": "The Three-Body Problem",
        "author": "Liu Cixin",
        "year": 2008,
        "lang": "zh",
        "basis": "Published 2008, author Liu Cixin (living), still under copyright worldwide."
    },
    {
        "slug": "the-dispossessed",
        "title": "The Dispossessed",
        "author": "Ursula K. Le Guin",
        "year": 1974,
        "lang": "en",
        "basis": "Published 1974, author Ursula K. Le Guin (1929-2018), still under copyright worldwide."
    },
    {
        "slug": "rocannons-world",
        "title": "Rocannon's World",
        "author": "Ursula K. Le Guin",
        "year": 1966,
        "lang": "en",
        "basis": "Published 1966, author Ursula K. Le Guin (1929-2018), still under copyright worldwide."
    },
    {
        "slug": "a-fire-upon-the-deep",
        "title": "A Fire Upon the Deep",
        "author": "Vernor Vinge",
        "year": 1992,
        "lang": "en",
        "basis": "Published 1992, author Vernor Vinge (1944-2024), still under copyright worldwide."
    }
]

def main():
    print("=== Applying T6: In-Copyright Receipts ===")

    for item in IN_COPYRIGHT_WORKS:
        slug = item["slug"]
        edition_id = f"copyright:{slug}"
        record_receipt(
            work_slug=slug,
            edition_id=edition_id,
            language=item["lang"],
            is_translation=0,
            rights="in_copyright",
            rights_basis=item["basis"],
            acquisition_class="absent",
            note="full text intentionally NOT acquired"
        )
        print(f"Recorded in_copyright receipt: {slug}")

    # Now update works table in a single transaction
    conn = sqlite3.connect("data/scifi_lexicon.db", timeout=30.0)
    with conn:
        for item in IN_COPYRIGHT_WORKS:
            slug = item["slug"]
            conn.execute("""
                UPDATE works
                SET has_full_text = 0,
                    text_path = NULL,
                    research_status = 'absent_copyright'
                WHERE slug = ?
            """, (slug,))

    conn.close()
    print("T6 completed successfully.")

if __name__ == "__main__":
    main()
