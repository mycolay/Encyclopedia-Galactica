"""
Звірка тверджень про Грінченка з набутим джерелом.

Вердикти жорсткі, «схоже на правду» не існує:

  CONTRADICTED  слова немає у словнику, АБО воно є, але в іншому томі
  CONFIRMED_VOL слово є, том збігається; сторінку цей передрук перевірити
                не дає (суцільна пагінація 1-2971 замість томової)
  NOT_FOUND     слово не витягнулося з твердження — нема що звіряти
  UNDECIDABLE   у твердженні немає посилання

Обмеження записується в кожен запис, а не замовчується.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import unicodedata
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.lexicography.lexicon_source import (
    parse_citation,
    extract_headword,
    expected_volume,
)

DB = "data/scifi_lexicon.db"
INDEX = Path("K:/scifi_library/lexicons/hrinchenko-1907-1909/headwords.json")
ARTIFACT = Path("K:/scifi_library/lexicons/hrinchenko-1907-1909/hrinchenko.txt")


def strip_accents(s: str) -> str:
    """Прибирає комбінований наголос U+0301, лишає літери."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s)
                   if unicodedata.category(ch) != "Mn").lower()


def normalize_old_orthography(s: str) -> str:
    """
    Дореформена орфографія словника: Трудникъ, вѣстникъ.
    Зводимо до сучасного вигляду для пошуку.
    """
    s = strip_accents(s)
    return (s.replace("ъ", "").replace("ѣ", "і").replace("и", "и")
             .replace("’", "").replace("'", "").strip())


import re

# Виправлені посилання несуть байтову координату в артефакті:
#   «Тяжкороб» (Грінченко, том 4, артефакт 2451234+58)
# Такі перевіряються ЧИТАННЯМ БАЙТІВ, а не розбором прози — той самий
# принцип, що й у свідків із творів: координата, а не твердження.
COORD_RE = re.compile(
    r"«([^»]+)»\s*\(Грінченко,\s*том\s*(\d),\s*артефакт\s*(\d+)\+(\d+)\)"
)


def verify_by_coordinates(model_text: str, data: bytes) -> Optional[Dict[str, Any]]:
    """Перевіряє всі координатні посилання у тексті. None — якщо їх немає."""
    matches = COORD_RE.findall(model_text or "")
    if not matches:
        return None
    checked, failed = [], []
    for word, vol, start, length in matches:
        start, length = int(start), int(length)
        line = data[start:start + length].decode("utf-8", errors="replace")
        if strip_accents(line).lower().startswith(strip_accents(word).lower()[:5]):
            checked.append(f"{word}@{start}")
        else:
            failed.append(f"{word}@{start} -> {line[:30]!r}")
    if failed:
        return {"verdict": "CONTRADICTED",
                "evidence": "координата не вказує на заявлене слово: " + "; ".join(failed)}
    return {"verdict": "CONFIRMED_COORD",
            "evidence": "усі моделі підтверджені байтовими координатами: "
                        + ", ".join(checked)}


def main() -> int:
    if not INDEX.exists():
        print(f"покажчик ще не побудовано: {INDEX}")
        return 1

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = idx["entries"]
    artifact_sha = idx["artifact_sha256"]

    # Захист від застарілого покажчика.
    #
    # Реальний випадок 2026-09-06: фонове завдання, запущене ДО виправлення
    # регулярки, завершилося ПІСЛЯ нього і мовчки затерло виправлений
    # покажчик старою версією. Звірка після цього дала б хибне спростування
    # для «бездоріжжя» вдруге. Покажчик мусить самозасвідчувати свою версію.
    expected_indexer = "build_hrinchenko_index.v2"
    if idx.get("indexer_version") != expected_indexer:
        print(
            f"ЗУПИНКА: покажчик побудовано версією "
            f"{idx.get('indexer_version') or '<без версії>'}, "
            f"а потрібна {expected_indexer}.\n"
            f"Перебудуйте: python scripts/build_hrinchenko_index.py"
        )
        return 2

    # мапа нормалізованої форми -> список записів
    lookup: dict[str, list[dict]] = {}
    for e in entries:
        key = normalize_old_orthography(e["headword"])
        lookup.setdefault(key, []).append(e)

    artifact_data = ARTIFACT.read_bytes()

    print(f"покажчик: {len(entries):,} реєстрових слів, "
          f"{len(lookup):,} унікальних форм")
    print(f"артефакт sha256: {artifact_sha[:32]}…\n")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    con.execute("DELETE FROM grinchenko_claim_checks")

    counts: dict[str, int] = {}
    rows = con.execute(
        "SELECT id, proposed_ukr_term, derivation_model FROM attestations "
        "WHERE register = 'proposed' AND derivation_model IS NOT NULL"
    ).fetchall()

    print(f"{'НЕОЛОГІЗМ':<20}{'СЛОВО-МОДЕЛЬ':<16}{'ТОМ':>4}{'ФАКТ':>5}  ВЕРДИКТ")
    for r in rows:
        model = r["derivation_model"]

        # Спершу — координатна перевірка. Якщо посилання її має, прози не
        # розбираємо взагалі: байти або на місці, або ні.
        by_coord = verify_by_coordinates(model, artifact_data)
        if by_coord:
            verdict = by_coord["verdict"]
            counts[verdict] = counts.get(verdict, 0) + 1
            con.execute(
                "INSERT INTO grinchenko_claim_checks "
                "(attestation_id, proposed_ukr_term, claim_text, verdict, "
                " evidence, checked_at_utc) VALUES (?,?,?,?,?,?)",
                (r["id"], r["proposed_ukr_term"], model,
                 "CONFIRMED" if verdict == "CONFIRMED_COORD" else verdict,
                 by_coord["evidence"], now),
            )
            print(f"{r['proposed_ukr_term'][:20]:<20}"
                  f"{'(за координатами)':<16}{'':>4}{'':>5}  {verdict}")
            continue

        cit = parse_citation(model)
        hw = extract_headword(model)

        if not cit:
            verdict, evidence, real_vol = "UNDECIDABLE", "у твердженні немає посилання", None
        elif not hw:
            verdict, evidence, real_vol = "NOT_FOUND", "слово-модель не витягується", None
        else:
            key = normalize_old_orthography(hw)
            found = lookup.get(key) or []
            if not found:
                verdict = "CONTRADICTED"
                evidence = f"«{hw}» у Словарі Грінченка не знайдено"
                real_vol = None
            else:
                real_vol = expected_volume(hw)
                if real_vol != cit.volume:
                    verdict = "CONTRADICTED"
                    evidence = (
                        f"«{hw}» є у словнику, але це том {real_vol}, "
                        f"а посилання каже том {cit.volume}"
                    )
                else:
                    verdict = "CONFIRMED_VOL"
                    evidence = (
                        f"«{hw}» знайдено у словнику, том {real_vol} збігається; "
                        f"сторінку цей передрук перевірити не дає "
                        f"(суцільна пагінація)"
                    )

        counts[verdict] = counts.get(verdict, 0) + 1
        con.execute(
            "INSERT INTO grinchenko_claim_checks "
            "(attestation_id, proposed_ukr_term, claim_text, claimed_headword, "
            " claimed_volume, claimed_page, verdict, evidence, checked_at_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (r["id"], r["proposed_ukr_term"], model, hw,
             cit.volume if cit else None, cit.page if cit else None,
             "CONFIRMED" if verdict == "CONFIRMED_VOL" else verdict,
             evidence, now),
        )
        print(f"{r['proposed_ukr_term'][:20]:<20}{(hw or '—')[:16]:<16}"
              f"{cit.volume if cit else '—':>4}{real_vol if real_vol else '—':>5}  {verdict}")

    con.commit()
    con.close()

    print()
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {k:<16}{v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
