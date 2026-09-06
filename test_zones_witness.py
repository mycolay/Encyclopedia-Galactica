"""
Регресійні тести на дефекти, знайдені в аудиті 2026-09-06.

Кожен тест відповідає конкретному хибному свідку, який пройшов у базу:
  - `robot`          байт 461 → англійський підзаголовок на титульній сторінці
  - `Time Traveller` байт 687 → вікно починалося у змісті (межа body = 738)

Ці тести мають бути ЧЕРВОНИМИ на старому коді і зеленими на новому.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from modules.corpus.witness import build_witness, find_occurrences
from modules.corpus.zones_llm import zone_for_span, extract_boundary_candidates

DB = "data/scifi_lexicon.db"


def _path(slug):
    con = sqlite3.connect(DB)
    row = con.execute("SELECT text_path FROM works WHERE slug = ?", (slug,)).fetchone()
    con.close()
    if not row or not row[0] or not Path(row[0]).exists():
        pytest.skip(f"немає тексту для {slug}")
    return row[0]


def _zones(path):
    zf = Path(path).parent / "zones.json"
    if not zf.exists():
        pytest.skip(f"немає zones.json поруч із {path}")
    return json.loads(zf.read_text(encoding="utf-8"))


def test_zone_for_span_rejects_straddling_window():
    """Вікно, що перетинає межу зон, не належить жодній зоні."""
    zones = {"zones": [
        {"kind": "toc", "byte_start": 345, "byte_end": 738},
        {"kind": "body", "byte_start": 738, "byte_end": 181770},
    ]}
    # саме той випадок, що потрапив у базу: вікно 687..887 через межу 738
    assert zone_for_span(zones, 687, 887) is None
    assert zone_for_span(zones, 800, 900) == "body"
    assert zone_for_span(zones, 400, 500) == "toc"


def test_time_machine_witness_window_inside_body():
    """Свідок 'Time Traveller' мусить мати ВСЕ вікно в body, не лише точку збігу."""
    path = _path("the-time-machine")
    zones = _zones(path)
    data = Path(path).read_bytes()

    accepted = None
    for idx, (pos, _form) in enumerate(find_occurrences(data, "Time Traveller")):
        w = build_witness(path, "Time Traveller", occurrence_index=idx)
        if w and zone_for_span(zones, w["byte_start"], w["byte_start"] + w["byte_len"]) == "body":
            accepted = w
            break

    assert accepted is not None, "жодного входження з вікном цілком у body"
    body = next(z for z in zones["zones"] if z["kind"] == "body")
    assert accepted["byte_start"] >= body["byte_start"], (
        f"вікно починається на {accepted['byte_start']}, "
        f"а body — з {body['byte_start']}"
    )


def test_rur_robot_not_attested_from_title_page():
    """
    'robot' не можна атестувати з англійського підзаголовка «(Rossum´s
    Universal Robots)» на титульній сторінці — це назва, а не вживання.
    """
    path = _path("rur-rossums-universal-robots")
    zones = _zones(path)
    data = Path(path).read_bytes()

    subtitle = data.find("(Rossum´s Universal Robots)".encode("utf-8"))
    if subtitle == -1:
        pytest.skip("підзаголовок не знайдено в цій редакції")

    assert zone_for_span(zones, subtitle, subtitle + 27) != "body", (
        "англійський підзаголовок на титулці позначено як body"
    )


def test_artifact_metadata_never_counts_as_body():
    """
    Наша власна YAML-метадата містить українські назви ('Машина часу',
    'роботи'). Жоден український збіг у ній не сміє потрапити в body.
    """
    for slug, term in [("the-time-machine", "Машина часу"),
                       ("rur-rossums-universal-robots", "роботи")]:
        path = _path(slug)
        zones = _zones(path)
        data = Path(path).read_bytes()
        for pos, _form in find_occurrences(data, term):
            zone = zone_for_span(zones, pos, pos + len(term.encode("utf-8")))
            assert zone != "body", (
                f"{slug}: '{term}' на байті {pos} зараховано до body — "
                "це наша метадата, не текст автора"
            )


def test_boundary_candidates_have_real_offsets():
    """Зміщення кандидатів мусять точно вказувати на свій рядок у файлі."""
    path = _path("the-time-machine")
    data = Path(path).read_bytes()
    for item in extract_boundary_candidates(data, 14000)[:25]:
        at = data[item["byte_offset"]: item["byte_offset"] + 200]
        assert at.decode("utf-8", errors="replace").lstrip().startswith(
            item["line"][:20]
        ), f"зміщення {item['byte_offset']} не вказує на «{item['line'][:40]}»"
