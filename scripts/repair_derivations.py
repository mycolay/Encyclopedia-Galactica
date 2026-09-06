"""
Заміна спростованих дериваційних моделей на засвідчені.

Дев'ять обґрунтувань посилалися на слова, яких у Грінченка немає:
трудник, ділороб, безчасний, скоропис, віщунство, мовознавство —
модель вигадала їх разом із томом і сторінкою. Ще три вказували не той том.

Тут кожна модель замінюється словом, ЗАСВІДЧЕНИМ у словнику, з байтовою
координатою в запечатаному артефакті. Жодне слово не вписується вручну:
скрипт бере його з покажчика і падає, якщо слова там немає.

Сам український неологізм лишається ПРОПОЗИЦІЄЮ (register='proposed').
Змінюється те, на що він спирається: вигадка -> засвідчений факт.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.lexicography.derivation_models import HrinchenkoIndex

DB = "data/scifi_lexicon.db"

# (неологізм, [слова-моделі], пояснення словотвору, тип деривації)
#
# derivation_type розрізняє принципово різні задачі:
#   cognate_recovery — слово вже є в українській, його треба відновити,
#                      а не творити (слов'янське джерело, спільний корінь);
#   coinage          — коріння немає, потрібне словотворення.
REPAIRS = [
    ("Тру́дник", ["Труд", "Тяжкороб"],
     "труд (корінь, засвідчений) + -ник (суфікс діяча). Проте засвідчене "
     "«Тяжкороб» — «исполняющій тяжелыя работы» — передає Чапекову robota "
     "точніше за новотвір, і має перевагу як відновлення, а не творення.",
     "cognate_recovery"),

    ("Чиноро́б", ["Чорнороб", "Тяжкороб"],
     "Модель «ділороб» у словнику відсутня. Засвідчені композити на -роб: "
     "«Чорнороб» (чернорабочій), «Тяжкороб», «Хлібороб». Саме вони, а не "
     "вигаданий зразок, показують продуктивність типу.",
     "cognate_recovery"),

    ("Мере́жище", ["Мережа", "Сховище"],
     "мереж- (засвідчене «Мережа» — невід з великими вічками) + -ище "
     "(локус; засвідчене «Сховище»). Обидві частини реальні; том «Сховища» "
     "виправлено з II на IV.",
     "coinage"),

    ("Безвча́сник", ["Безчасу", "Вість"],
     "Засвідчене «Безчасу» — «преждевременно, несвоевременно» — доводить "
     "продуктивність без- на основі час-. Попередня модель «безчасний» у "
     "словнику відсутня.",
     "coinage"),

    ("Скорові́ст", ["Скоробреха", "Вість"],
     "Композити на скоро- засвідчені («Скоробреха», «Скородільник»); "
     "«Вість» засвідчене окремо. Попередня модель «скоропис» відсутня.",
     "coinage"),

    ("Душолітопи́сництво", ["Літопись", "Будівництво"],
     "«Літопись» і суфікс -ництво засвідчені («Будівництво», «Видавництво»). "
     "Попередня модель «віщунство» у словнику відсутня.",
     "coinage"),

    ("Масові́дство", ["Мисливство", "Знавець"],
     "«Мовознавство» у словнику відсутнє — це термін XX ст. Продуктивність "
     "типу показують засвідчені «Мисливство» і «Знавець».",
     "coinage"),

    ("Мислеве́т", ["Мисль", "Знавець"],
     "«Мисль» і «Знавець» засвідчені. Том «Віщуна» виправлено з II на I.",
     "coinage"),

    ("Думолічи́льник", ["Дума", "Лічильник"],
     "«Дума» і «Лічильник» («счетчикъ») засвідчені обидва. Це прямий "
     "відповідник гербертівського human computer. Томи виправлено.",
     "coinage"),
]


def main(apply: bool = False) -> int:
    idx = HrinchenkoIndex()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    # додати колонку типу деривації, якщо її ще немає
    cols = {r[1] for r in con.execute("PRAGMA table_info(attestations)")}
    if "derivation_type" not in cols:
        if apply:
            con.execute(
                "ALTER TABLE attestations ADD COLUMN derivation_type TEXT "
                "CHECK (derivation_type IN "
                "('cognate_recovery','coinage','calque') OR derivation_type IS NULL)"
            )
            print("додано колонку derivation_type")

    now = datetime.now(timezone.utc).isoformat()
    repaired = missing = 0

    print(f"{'НЕОЛОГІЗМ':<20}{'ЗАСВІДЧЕНІ МОДЕЛІ':<34}{'ТИП':<18}")
    for neologism, models, rationale, dtype in REPAIRS:
        checks = [idx.verify_model(w) for w in models]
        absent = [c["word"] for c in checks if c["verdict"] != "ATTESTED"]
        if absent:
            missing += 1
            print(f"{neologism[:20]:<20}ЗУПИНКА: не засвідчено {absent}")
            continue

        cites = "; ".join(
            f"«{c['word']}» (Грінченко, том {c['volume']}, "
            f"артефакт {c['byte_start']}+{c['byte_len']})"
            for c in checks
        )
        new_model = f"{rationale} Моделі: {cites}."
        repaired += 1
        shown = ", ".join(c["word"] for c in checks)[:33]
        print(f"{neologism[:20]:<20}{shown:<34}{dtype:<18}")

        if apply:
            con.execute(
                "UPDATE attestations SET derivation_model = ?, "
                "grinchenko_root = ?, root_attested_in_grinchenko = 1, "
                "derivation_type = ?, verified_at_utc = ? "
                "WHERE proposed_ukr_term = ? AND register = 'proposed'",
                (new_model, checks[0]["word"], dtype, now, neologism),
            )

    if apply:
        con.commit()
    con.close()

    print()
    print(f"{'ЗАСТОСОВАНО' if apply else 'ПРОБНИЙ ПРОГІН'}: "
          f"виправлено {repaired}, зупинено {missing}")
    if not apply:
        print("для запису: python scripts/repair_derivations.py --apply")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
