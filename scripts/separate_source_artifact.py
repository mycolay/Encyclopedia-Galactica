"""
Розділення артефакту: першоджерело окремо від нашої метадати.

Проблема, яку це закриває.
`full_text.md` починається з YAML-шапки, яку згенерували МИ, і в ній є
українські назви (`title_ukr: "Машина часу"`). Свідки дивляться байтовими
координатами саме в цей файл, тому пошук українського терміна може дати
«свідка», що засвідчує наш власний переклад назви, а не автора.
Перевірено 2026-09-06: 4 таких збіги в корпусі.

Рішення: `source.txt` містить ТІЛЬКИ очищений текст першоджерела.
Свідки вказують у нього.

Зони НЕ перегенеровуються моделлю: текст після шапки байт-у-байт той самий,
тому всі зміщення просто зсуваються на довжину шапки. Це детерміновано,
миттєво і не залежить від повторного прогону LLM.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

DB = "data/scifi_lexicon.db"


def split_front_matter(data: bytes) -> tuple[bytes, bytes]:
    """Повертає (шапка, текст). Якщо шапки немає — (b'', data)."""
    if not data.startswith(b"---"):
        return b"", data
    # друга межа '---' на власному рядку
    idx = data.find(b"\n---", 3)
    if idx == -1:
        return b"", data
    end = idx + len(b"\n---")
    # проковтнути перевід рядка й порожні рядки одразу після межі
    while end < len(data) and data[end] in (0x0A, 0x0D):
        end += 1
    return data[:end], data[end:]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(apply: bool = False) -> int:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT id, title_orig, text_path FROM works "
        "WHERE has_full_text = 1 ORDER BY title_orig"
    ).fetchall()

    print(f"{'ТВІР':<44}{'ШАПКА':>7}{'ЗСУВ ЗОН':>10}  ПЕРЕВІРКА")
    changed = failed = 0

    for work_id, title, path in rows:
        p = Path(path)
        if not p.exists():
            print(f"{title[:44]:<44}{'—':>7}{'—':>10}  файл відсутній")
            failed += 1
            continue

        data = p.read_bytes()
        header, body = split_front_matter(data)
        if not header:
            print(f"{title[:44]:<44}{0:>7}{0:>10}  шапки немає, пропуск")
            continue

        src_path = p.parent / "source.txt"
        zones_path = p.parent / "zones.json"

        # зсув зон = довжина шапки
        shift = len(header)
        ok = "—"
        if zones_path.exists():
            z = json.loads(zones_path.read_text(encoding="utf-8"))
            body_zone = next((x for x in z["zones"] if x["kind"] == "body"), None)
            if body_zone:
                old_start = body_zone["byte_start"]
                new_start = old_start - shift
                # контроль: байти за новим зміщенням у source мусять збігтися
                # зі старими байтами за старим зміщенням у full_text
                ok = "OK" if data[old_start:old_start + 40] == body[new_start:new_start + 40] else "РОЗБІЖНІСТЬ"

        print(f"{title[:44]:<44}{shift:>7}{-shift:>10}  {ok}")

        if apply and ok in ("OK", "—"):
            src_path.write_bytes(body)
            if zones_path.exists():
                z = json.loads(zones_path.read_text(encoding="utf-8"))
                for zone in z["zones"]:
                    zone["byte_start"] = max(0, zone["byte_start"] - shift)
                    zone["byte_end"] = max(0, zone["byte_end"] - shift)
                z["artifact"] = "source.txt"
                z["shifted_from_full_text_by"] = shift
                z["source_sha256"] = sha256(body)
                zones_path.write_text(
                    json.dumps(z, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            con.execute(
                "UPDATE works SET text_path = ? WHERE id = ?", (str(src_path), work_id)
            )
            changed += 1
        elif ok == "РОЗБІЖНІСТЬ":
            failed += 1

    if apply:
        con.commit()
    con.close()

    print()
    print(f"{'ЗАСТОСОВАНО' if apply else 'ПРОБНИЙ ПРОГІН'}: змінено {changed}, помилок {failed}")
    if not apply:
        print("для застосування: python scripts/separate_source_artifact.py --apply")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
