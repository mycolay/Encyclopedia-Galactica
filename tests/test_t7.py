import os
import sqlite3

def test_catalog_matches_db():
    assert os.path.exists("docs/LIBRARY_CATALOG.md"), "docs/LIBRARY_CATALOG.md not found"
    content = open("docs/LIBRARY_CATALOG.md", "rb").read().decode("utf-8")

    c = sqlite3.connect("data/scifi_lexicon.db")
    n_works = c.execute("SELECT count(*) FROM works").fetchone()[0]
    n_verified = c.execute("SELECT count(*) FROM works WHERE has_full_text=1").fetchone()[0]
    n_copy = c.execute("SELECT count(*) FROM acquisition_receipts WHERE rights='in_copyright'").fetchone()[0]
    n_synth = c.execute("SELECT count(*) FROM acquisition_receipts WHERE acquisition_class='synthetic'").fetchone()[0]

    assert f"Усього творів у каталозі:        {n_works}" in content
    assert f"З перевіреним повним текстом:    {n_verified}" in content
    assert f"Відсутні через копірайт:         {n_copy}" in content
    assert f"У карантині (синтетика):         {n_synth}" in content
    print("T7 TEST PASSED: docs/LIBRARY_CATALOG.md matches database SELECTs exactly!")

if __name__ == "__main__":
    test_catalog_matches_db()
