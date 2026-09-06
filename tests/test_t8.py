import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import sqlite3

def test_t8():
    conn = sqlite3.connect('data/scifi_lexicon.db')
    results = []
    for label, sql in [
        ('attested без свідка', "insert into attestations(term_orig,register) values('x','attested')"),
        ('proposed без укр. терміна', "insert into attestations(term_orig,register) values('x','proposed')")
    ]:
        try:
            conn.execute(sql)
            print(f'ПОМИЛКА, CHECK не спрацював: {label}')
            results.append(False)
        except sqlite3.IntegrityError:
            print(f'OK, відхилено: {label}')
            results.append(True)
    conn.rollback()
    conn.close()
    assert all(results), "Not all T8 checks passed"
    print("T8 TEST PASSED!")

if __name__ == '__main__':
    test_t8()
