"""
Збір свідків по корпусу — детермінований, без LLM.

Це КРОК 2 інвертованого циклу (ЛОКАЛІЗАЦІЯ). Модель тут не бере участі
взагалі: код шукає термін у повному тексті, будує координату і перевіряє її.
Кандидати задані списком; LLM-пропозиція (КРОК 1) додає нові терміни згодом,
але доказом стає лише те, що пройшло цю перевірку.

Правила, які тут виконуються без винятків:
  * враховується лише зона 'body' і лише коли ВСЕ вікно свідка в ній;
  * свідок мусить пройти verify_witness (5 бінарних перевірок);
  * рік атестації береться з року твору, але сам факт — з координати;
  * нічого не вигадується: немає збігу — немає запису.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.corpus.witness import build_witness, verify_witness, find_occurrences
from modules.corpus.zones_llm import zone_for_span

DB = "data/scifi_lexicon.db"
VERIFIER_VERSION = "witness.v1+zones_llm.v1"

# Терміни-кандидати за творами. Це відомі фантастичні поняття й авторські
# новотвори; кожен ще мусить бути ЗНАЙДЕНИЙ у тексті, інакше не потрапить.
CANDIDATES: dict[str, list[str]] = {
    "the-time-machine": ["Time Traveller", "Time Machine", "Morlock", "Eloi",
                         "Fourth Dimension", "Palaeontology"],
    "the-war-of-the-worlds": ["Martian", "Heat-Ray", "Black Smoke",
                              "handling-machine", "fighting-machine", "red weed"],
    "the-invisible-man": ["invisible man", "refractive index", "albino"],
    "the-island-of-doctor-moreau": ["Beast Folk", "vivisection", "House of Pain",
                                    "Sayer of the Law"],
    "the-first-men-in-the-moon": ["Cavorite", "Selenite", "sphere", "Grand Lunar"],
    "when-the-sleeper-wakes": ["Sleeper", "Council", "aeroplane", "Babble Machine"],
    "frankenstein": ["natural philosophy", "galvanism", "creature", "daemon"],
    "flatland": ["Flatland", "Spaceland", "Lineland", "Pointland",
                 "Third Dimension", "Circle"],
    "twenty-thousand-leagues-under-the-sea": ["Nautilus", "Captain Nemo",
                                              "submarine", "electricity"],
    "from-the-earth-to-the-moon": ["Gun Club", "Columbiad", "projectile"],
    "around-the-moon": ["projectile", "disc", "lunar"],
    "journey-to-the-center-of-the-earth": ["Runic", "Icthyosaurus", "Plesiosaurus"],
    "robur-the-conqueror": ["Albatross", "aeronef", "Robur"],
    "a-princess-of-mars": ["Barsoom", "Thark", "thoat", "calot", "Tharks",
                           "eighth ray", "radium"],
    "the-gods-of-mars": ["Barsoom", "Therns", "Iss", "Omean"],
    "the-land-that-time-forgot": ["Caspak", "Caprona", "Wieroo"],
    "rur-rossums-universal-robots": ["Robot", "Roboti", "robota", "protoplazma"],
    "herland": ["Herland", "parthenogenesis", "bi-sexual"],
    "looking-backward": ["credit card", "industrial army", "nationalism"],
    "erewhon": ["Erewhon", "Musical Banks", "machines"],
    "the-coming-race": ["Vril", "Vril-ya", "An-a", "Gy-ei"],
    "micromegas": ["Micromégas", "Sirius", "Saturnien"],
    "the-blazing-world": ["Blazing-World", "Bear-men", "Fox-men", "Emperess"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(apply: bool = False) -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    works = {
        r["slug"]: r
        for r in con.execute(
            "SELECT id, slug, title_orig, year, author_id, text_path "
            "FROM works WHERE has_full_text = 1"
        )
    }

    collected = rejected_zone = rejected_absent = rejected_verify = 0
    rows_to_insert = []

    for slug, terms in CANDIDATES.items():
        w = works.get(slug)
        if not w:
            continue
        path = w["text_path"]
        if not path or not Path(path).exists():
            continue
        zones_file = Path(path).parent / "zones.json"
        if not zones_file.exists():
            print(f"  {slug}: немає zones.json, пропуск")
            continue
        zones = json.loads(zones_file.read_text(encoding="utf-8"))
        data = Path(path).read_bytes()

        for term in terms:
            occurrences = find_occurrences(data, term)
            if not occurrences:
                rejected_absent += 1
                continue

            chosen = None
            for idx in range(len(occurrences)):
                cand = build_witness(path, term, occurrence_index=idx)
                if not cand:
                    continue
                span = zone_for_span(
                    zones, cand["byte_start"], cand["byte_start"] + cand["byte_len"]
                )
                if span != "body":
                    continue
                status, reason, _quote = verify_witness(cand, path, term)
                if status != "ACCEPT":
                    rejected_verify += 1
                    continue
                chosen = cand
                break

            if not chosen:
                rejected_zone += 1
                continue

            collected += 1
            rows_to_insert.append(
                (
                    term, w["id"], w["year"], "attested", "body",
                    chosen["matched_form"],
                    f"urn:cts:sf:{slug}:{chosen['byte_start']}",
                    chosen["artifact_sha256"], chosen["byte_start"],
                    chosen["byte_len"], chosen["window_sha256"],
                    utc_now(), VERIFIER_VERSION,
                )
            )

    print(f"{'':-<64}")
    print(f"знайдено і верифіковано свідків : {collected}")
    print(f"терміна немає в тексті          : {rejected_absent}")
    print(f"жодного входження в зоні body   : {rejected_zone}")
    print(f"не пройшли verify_witness       : {rejected_verify}")

    if apply and rows_to_insert:
        # Анулювати попередні attested: вони вказували у full_text.md,
        # якого більше немає як артефакту свідків.
        con.execute("DELETE FROM attestations WHERE register = 'attested'")
        con.executemany(
            "INSERT INTO attestations "
            "(term_orig, work_id, year, register, zone, matched_form, cts_urn, "
            " artifact_sha256, byte_start, byte_len, window_sha256, "
            " verified_at_utc, verifier_version) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows_to_insert,
        )
        con.commit()
        print(f"\nЗАПИСАНО в базу: {len(rows_to_insert)}")
    elif not apply:
        print("\nПРОБНИЙ ПРОГІН. Для запису: python scripts/collect_witnesses.py --apply")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
