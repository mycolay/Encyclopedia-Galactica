"""
Структурна сегментація твору через LLM з детермінованою перевіркою.

Принцип той самий, що й у свідках: модель НЕ повертає байтових зміщень.
Вона повертає ДОСЛІВНИЙ ЯКІР — рядок, який має існувати у файлі.
Код шукає цей якір сам і обчислює зміщення. Якір не знайдено — відмова.

Це знімає обмеження regex-евристик, які ламаються на нестандартних
виданнях (чеська драма з `OSOBY` замість `CHAPTER I`, епістолярний роман
без розділів, антологія тощо), і водночас не дає моделі права на вигадку:
її вихід — це запит на пошук, а не факт.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.autoresearch.llm_client import LocalLLMClient

logger = logging.getLogger("AutoSciFi.ZonesLLM")

SCHEMA_VERSION = "zones_llm.v1"

# Скільки байтів віддавати моделі. Межі твору живуть на краях файлу.
HEAD_BYTES = 14000
TAIL_BYTES = 8000

# Мінімальна довжина якоря.
#
# УВАГА, історія помилки. Тут стояло 12 — підібране на англійських романах,
# де перше речення довге. Це мовчки відкидало ПРАВИЛЬНІ відповіді для драми:
# модель повернула «Předehra» (8 символів, байт 1948) і «OPONA» (5 символів,
# байт 37290) — обидва правильні й обидва є у файлі, але фільтр відсікав їх
# ДО пошуку. Провал списали на чеську мову; чеська була ні до чого.
#
# Слов'янська драма позначає межі одним словом. Порог має бути мінімальним,
# а унікальність перевірятися ПІСЛЯ пошуку — за кількістю збігів, а не за
# довжиною рядка.
MIN_ANCHOR_LEN = 3
MAX_ANCHOR_LEN = 120

# Унікальність якоря — за кількістю збігів, не за довжиною рядка.
MAX_ANCHOR_OCCURRENCES = 3

# Службові рядки Project Gutenberg та видавця. Початком твору бути не можуть,
# тому взагалі не потрапляють до списку кандидатів: чого немає у списку —
# того не можна обрати. Перевірено: модель обирала «Produced by Norm Wolcott»
# як початок оповіді у «A Journey to the Centre of the Earth».
BOILERPLATE_RE = re.compile(
    r"(Produced by|Transcribed by|E-?text prepared|Proofreading Team|"
    r"Distributed Proofread|Thanks to .{0,40}for creating|anonymous donor|"
    r"PROJECT GUTENBERG|gutenberg\.org|Updated editions will replace|"
    r"START OF (THE|THIS) PROJECT|END OF (THE|THIS) PROJECT|"
    r"Character set encoding|Release Date|Posting Date|\[Illustration)",
    re.IGNORECASE,
)

SYSTEM_PROMPT = (
    "Ти — текстолог, що готує критичне видання. Твоє завдання — визначити, "
    "де саме починається і закінчується АВТОРСЬКИЙ ТЕКСТ твору, відділивши "
    "його від службового обрамлення: метаданих, ліцензій, подяк, титульної "
    "сторінки, змісту, списку дійових осіб, передмов видавця, післямов і "
    "колофонів. Відповідай ВИКЛЮЧНО валідним JSON."
)


def _build_prompt(head: str, tail: str, hint: str = "") -> str:
    return f"""Нижче — ПОЧАТОК і КІНЕЦЬ файлу літературного твору.

{hint}

=== ПОЧАТОК ФАЙЛУ ===
{head}
=== КІНЕЦЬ ФРАГМЕНТА ===

=== КІНЕЦЬ ФАЙЛУ ===
{tail}
=== КІНЕЦЬ ФРАГМЕНТА ===

Визнач межі авторського тексту.

ВАЖЛИВО:
- Не повертай номерів байтів чи рядків. Повертай ДОСЛІВНІ рядки з файлу.
- Якір мусить бути скопійований СИМВОЛ У СИМВОЛ з наведеного фрагмента.
- body_start_anchor — перший рядок власне твору. Для роману це перший
  рядок першого розділу (не заголовок «CHAPTER I», а сам текст, якщо
  заголовок є частиною обрамлення — або заголовок, якщо він частина твору).
  Для драми — перша ремарка або репліка ПІСЛЯ списку дійових осіб.
- body_end_anchor — останній рядок власне твору, перед ліцензією чи
  післямовою видавця.
- toc_start_anchor / toc_end_anchor — якщо у файлі є зміст; інакше null.

Формат:
{{
  "body_start_anchor": "дослівний рядок",
  "body_end_anchor": "дослівний рядок",
  "toc_start_anchor": "дослівний рядок або null",
  "toc_end_anchor": "дослівний рядок або null",
  "work_kind": "novel | play | novella | collection",
  "reasoning": "одне речення, чому саме тут межа"
}}"""


def extract_boundary_candidates(
    data: bytes, limit_bytes: int, from_end: bool = False, max_items: int = 220
) -> List[Dict[str, Any]]:
    """
    Витягує змістовні рядки-кандидати меж РАЗОМ з їхніми байтовими зміщеннями.

    Модель потім лише ОБИРАЄ індекс зі списку. Зміщення обчислює код, тому
    поверхні для вигадки не лишається: модель не транскрибує текст, а вказує
    на вже знайдений код рядок. Це знімає провал на чеській діакритиці.
    """
    text = data.decode("utf-8", errors="replace")
    if from_end:
        region_start_char = len(text) - len(data[-limit_bytes:].decode("utf-8", errors="replace"))
    else:
        region_start_char = 0
    region = text[region_start_char:] if from_end else text[:limit_bytes]

    items: List[Dict[str, Any]] = []
    char_pos = region_start_char
    for line in region.splitlines(keepends=True):
        stripped = line.strip()
        # Рядки, які ФІЗИЧНО не можуть бути початком твору, зі списку прибираємо:
        # модель кілька разів обирала кредит транскриптора Gutenberg як початок
        # оповіді (перевірено на «A Journey to the Centre of the Earth» та
        # «All Around the Moon»). Чого немає у списку — того не можна обрати.
        if len(stripped) >= 3 and not BOILERPLATE_RE.search(stripped):
            items.append(
                {
                    "index": len(items),
                    "byte_offset": len(text[:char_pos].encode("utf-8")),
                    "line": stripped[:160],
                }
            )
        char_pos += len(line)
    if from_end and len(items) > max_items:
        items = items[-max_items:]
        for n, it in enumerate(items):
            it["index"] = n
    return items[:max_items]


def _find_anchor(data: bytes, anchor: str) -> Optional[int]:
    """Шукає якір дослівно, потім із нормалізованими пробілами. Повертає байт."""
    if not anchor or len(anchor.strip()) < MIN_ANCHOR_LEN:
        return None
    needle = anchor.strip()

    # 1. дослівний пошук; унікальність перевіряємо ПІСЛЯ, а не через довжину
    raw = needle.encode("utf-8")
    pos = data.find(raw)
    if pos != -1:
        occurrences = data.count(raw)
        if occurrences > MAX_ANCHOR_OCCURRENCES:
            logger.warning(
                "Якір %r трапляється %d разів — неунікальний, відхилено.",
                needle[:40], occurrences,
            )
            return None
        return pos

    # 2. толерантний до пробілів і переносів рядків
    text = data.decode("utf-8", errors="replace")
    pattern = r"\s+".join(re.escape(tok) for tok in needle.split())
    m = re.search(pattern, text)
    if m:
        return len(text[: m.start()].encode("utf-8"))
    return None


def _zones_from_offsets(
    size: int,
    body_start: int,
    body_end: int,
    toc_start: Optional[int],
    toc_end: Optional[int],
) -> List[Dict[str, Any]]:
    zones: List[Dict[str, Any]] = []
    if toc_start is not None and toc_end is not None and toc_start < toc_end <= body_start:
        zones.append({"kind": "front_matter", "byte_start": 0, "byte_end": toc_start})
        zones.append({"kind": "toc", "byte_start": toc_start, "byte_end": toc_end})
        if toc_end < body_start:
            zones.append({"kind": "front_matter", "byte_start": toc_end, "byte_end": body_start})
    else:
        zones.append({"kind": "front_matter", "byte_start": 0, "byte_end": body_start})
    zones.append({"kind": "body", "byte_start": body_start, "byte_end": body_end})
    if body_end < size:
        zones.append({"kind": "back_matter", "byte_start": body_end, "byte_end": size})
    return [z for z in zones if z["byte_end"] > z["byte_start"]]


SELECT_SYSTEM = (
    "Ти — текстолог, що готує критичне видання. Тобі дають пронумеровані рядки "
    "з початку і кінця файлу. Ти лише ОБИРАЄШ номери рядків, де починається і "
    "закінчується авторський текст твору. Нічого не переписуй. "
    "Відповідай ВИКЛЮЧНО валідним JSON."
)


def _select_prompt(head_items, tail_items) -> str:
    h = "\n".join(f'{it["index"]}: {it["line"]}' for it in head_items)
    t = "\n".join(f'{it["index"]}: {it["line"]}' for it in tail_items)
    return f"""ПОЧАТОК ФАЙЛУ (пронумеровані рядки):
{h}

КІНЕЦЬ ФАЙЛУ (пронумеровані рядки, окрема нумерація):
{t}

Визнач межі ВЛАСНЕ АВТОРСЬКОГО ТЕКСТУ, відкинувши службове обрамлення:
метадані, ліцензії й подяки, титульну сторінку, зміст, список дійових осіб,
передмову видавця, післямову, колофон.

- body_start_index: номер рядка з ПЕРШОГО списку, з якого починається твір.
  Для роману — перший рядок ОПОВІДІ (речення, а не заголовок).
  Для драми — перша ремарка або репліка ПІСЛЯ списку дійових осіб
  (після OSOBY / DRAMATIS PERSONAE).

  УВАГА, типові помилки:
  * Кілька назв розділів підряд («CHAPTER I. ... / CHAPTER II. ...») — це
    ЗМІСТ, навіть якщо заголовка «CONTENTS» немає. Твір починається ПІСЛЯ нього.
  * Назва твору й ім'я автора — це титульна сторінка, а не початок твору.
  * Авторська передмова (FOREWORD, PREFACE) — частина твору, її ВКЛЮЧАЙ.
    Передмова видавця чи перекладача — обрамлення, її ВИКЛЮЧАЙ.
- body_end_index: номер рядка з ДРУГОГО списку, яким твір закінчується.
- toc_start_index / toc_end_index: межі змісту в ПЕРШОМУ списку, або null.

Формат:
{{"body_start_index": ціле, "body_end_index": ціле,
  "toc_start_index": ціле або null, "toc_end_index": ціле або null,
  "work_kind": "novel|play|novella|collection",
  "reasoning": "одне речення"}}"""


def detect_zones_by_selection(
    file_path: str, llm: Optional[LocalLLMClient] = None
) -> Dict[str, Any]:
    """
    Основна стратегія: код витягує кандидатів, модель обирає індекси.

    Модель не транскрибує жодного символу, тому діакритика, лапки й
    нестандартні розкладки більше не є точкою відмови.
    """
    path = Path(file_path)
    data = path.read_bytes()
    size = len(data)

    head_items = extract_boundary_candidates(data, HEAD_BYTES, from_end=False)
    tail_items = extract_boundary_candidates(data, TAIL_BYTES, from_end=True)
    if not head_items or not tail_items:
        return {"schema_version": SCHEMA_VERSION, "status": "no_candidates", "zones": []}

    llm = llm or LocalLLMClient(model_name="qwen3.5:27b")
    if not llm.is_available():
        return {"schema_version": SCHEMA_VERSION, "status": "llm_unavailable", "zones": []}

    try:
        res = llm.generate(
            prompt=_select_prompt(head_items, tail_items),
            system_prompt=SELECT_SYSTEM,
            json_mode=True,
            temperature=0.0,
        )
        cand = res.get("json", {}) or {}
    except Exception as exc:
        logger.error("LLM помилка вибору: %s", exc)
        return {"schema_version": SCHEMA_VERSION, "status": "llm_error", "zones": []}

    def pick(items, idx):
        if idx is None:
            return None
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return None
        return items[idx] if 0 <= idx < len(items) else None

    bs = pick(head_items, cand.get("body_start_index"))
    be = pick(tail_items, cand.get("body_end_index"))
    ts = pick(head_items, cand.get("toc_start_index"))
    te = pick(head_items, cand.get("toc_end_index"))

    if not bs or not be or bs["byte_offset"] >= be["byte_offset"]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "invalid_selection",
            "zones": [],
            "raw": cand,
        }

    body_end = min(size, be["byte_offset"] + len(be["line"].encode("utf-8")))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "llm_verified",
        "method": "selection",
        "work_kind": cand.get("work_kind"),
        "reasoning": cand.get("reasoning"),
        "anchors": {
            "body_start": bs["line"],
            "body_end": be["line"],
            "toc_start": ts["line"] if ts else None,
            "toc_end": te["line"] if te else None,
        },
        "zones": _zones_from_offsets(
            size,
            bs["byte_offset"],
            body_end,
            ts["byte_offset"] if ts else None,
            (te["byte_offset"] + len(te["line"].encode("utf-8"))) if te else None,
        ),
        "human_confirmed": False,
    }


def detect_zones_llm(
    file_path: str,
    llm: Optional[LocalLLMClient] = None,
    max_attempts: int = 2,
) -> Dict[str, Any]:
    """
    Повертає карту зон із якорями. Кожна межа підтверджена знайденим у файлі
    якорем — інакше межа не встановлюється.

    status:
      'llm_verified'   — усі якорі знайдено в файлі
      'llm_unverified' — модель відповіла, але якорі не знайдено (межі не взято)
      'llm_unavailable'— модель недоступна
    """
    path = Path(file_path)
    data = path.read_bytes()
    size = len(data)
    head = data[:HEAD_BYTES].decode("utf-8", errors="replace")
    tail = data[-TAIL_BYTES:].decode("utf-8", errors="replace")

    llm = llm or LocalLLMClient(model_name="qwen3.5:27b")
    if not llm.is_available():
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "llm_unavailable",
            "zones": [],
            "anchors": {},
        }

    hint = ""
    for attempt in range(1, max_attempts + 1):
        try:
            res = llm.generate(
                prompt=_build_prompt(head, tail, hint),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
                temperature=0.0,
            )
            cand = res.get("json", {}) or {}
        except Exception as exc:
            logger.error("LLM помилка (спроба %s): %s", attempt, exc)
            continue

        bs = _find_anchor(data, cand.get("body_start_anchor") or "")
        be = _find_anchor(data, cand.get("body_end_anchor") or "")
        ts = _find_anchor(data, cand.get("toc_start_anchor") or "")
        te = _find_anchor(data, cand.get("toc_end_anchor") or "")

        missing = [
            name
            for name, val, off in (
                ("body_start_anchor", cand.get("body_start_anchor"), bs),
                ("body_end_anchor", cand.get("body_end_anchor"), be),
            )
            if val and off is None
        ]

        if bs is not None and be is not None and bs < be:
            # кінець якоря, а не початок — щоб останній рядок увійшов у body
            be_full = be + len((cand.get("body_end_anchor") or "").strip().encode("utf-8"))
            be_full = min(be_full, size)
            if te is not None:
                te = te + len((cand.get("toc_end_anchor") or "").strip().encode("utf-8"))
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "llm_verified",
                "attempt": attempt,
                "work_kind": cand.get("work_kind"),
                "reasoning": cand.get("reasoning"),
                "anchors": {
                    "body_start": cand.get("body_start_anchor"),
                    "body_end": cand.get("body_end_anchor"),
                    "toc_start": cand.get("toc_start_anchor"),
                    "toc_end": cand.get("toc_end_anchor"),
                },
                "zones": _zones_from_offsets(size, bs, be_full, ts, te),
                "human_confirmed": False,
            }

        hint = (
            "УВАГА: попередня спроба невдала — цих рядків у файлі немає "
            f"дослівно: {missing}. Скопіюй якір ТОЧНО з наведеного фрагмента."
        )
        logger.warning("Якорі не знайдено (спроба %s): %s", attempt, missing)

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "llm_unverified",
        "zones": [],
        "anchors": {},
        "human_confirmed": False,
    }


def zone_for_span(zones_data: Dict[str, Any], start: int, end: int) -> Optional[str]:
    """
    Зона для ВСЬОГО діапазону, а не для точки.

    Повертає назву зони, лише якщо весь [start, end) лежить у ній.
    Якщо діапазон перетинає межу — None. Це закриває дефект, через який
    вікно з зоною body починалося у змісті.
    """
    for z in zones_data.get("zones", []):
        if z["byte_start"] <= start and end <= z["byte_end"]:
            return z["kind"]
    return None


def save_zones(file_path: str, zones_data: Dict[str, Any]) -> Path:
    """Кладе zones.json поруч із текстом — карта йде під печатку разом із ним."""
    out = Path(file_path).parent / "zones.json"
    out.write_text(json.dumps(zones_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
