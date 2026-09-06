"""
Словник Грінченка як ДЖЕРЕЛО З ЧЕКОМ ПОХОДЖЕННЯ.

Той самий метод свідка, що й для корпусу, застосований до словника.

Навіщо це потрібно.
У базі лежать 14 тверджень на кшталт «Словарь Грінченка, т. IV, с. 293:
Трудникъ». Їх згенерувала мовна модель, яка словника не бачила. Це рівно
та сама помилка, з якої почався аудит, просто в іншому місці: правдоподібне
посилання, яке неможливо перевірити.

Тут заводиться перевірна основа: артефакт із відомим sha256, витягнуті
статті з номерами тому й сторінки, і функція звірки, яка каже про кожне
твердження CONFIRMED / CONTRADICTED / NOT_FOUND — і ніколи «схоже на правду».

Первинне джерело — скан друкованого видання, бо саме на його пагінацію
посилаються наші дані. HTML-передруки використовуються як допоміжна звірка,
не як основа.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "lexicon_source.v0"

# Томи 4-томного видання 1907-1909 і літери, які вони покривають.
# Використовується як ДЕТЕКТОР СУПЕРЕЧНОСТЕЙ: якщо посилання каже «том I»
# для слова на «М», твердження хибне ще до звіряння сторінки.
VOLUME_RANGES = [
    (1, "А", "Ж"),
    (2, "З", "Н"),
    (3, "О", "П"),
    (4, "Р", "Я"),
]

UKR_ALPHABET = "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ"


def expected_volume(headword: str) -> Optional[int]:
    """Том, у якому слово мусить бути за абеткою. None — якщо не визначити."""
    if not headword:
        return None
    first = headword.strip().upper()[:1]
    # Ъ/Ы/Э у дореформеній орфографії; І та И окремо
    first = {"Ъ": "", "Ы": "И", "Э": "Е"}.get(first, first)
    if first not in UKR_ALPHABET:
        return None
    idx = UKR_ALPHABET.index(first)
    for vol, lo, hi in VOLUME_RANGES:
        if UKR_ALPHABET.index(lo) <= idx <= UKR_ALPHABET.index(hi):
            return vol
    return None


# УВАГА: у наших даних римські числівники писані КИРИЛИЧНИМИ літерами —
# «т. ІІ» це І+І (U+0406), а не латинське II. Через це 11 із 14 посилань
# спершу взагалі не розпарсились. Приймаємо обидві абетки.
LATIN_I, CYR_I = "IVXivx", "ІVХіvх"
# «с.» перед номером сторінки НЕ обов'язкове: у наших даних трапляється
# і «т. IV, с. 293», і «Грінченко І, 73» — другий формат спершу випадав.
CITATION_RE = re.compile(
    r"(?:т\.\s*)?\b([IVXІVХivxіvх]{1,4}|[1-4])\s*[,;]\s*(?:с\.?|ст\.?)?\s*(\d{1,4})",
    re.IGNORECASE,
)


def _normalize_roman(s: str) -> str:
    """Кирилиця-двійник -> латиниця: І->I, Х->X, У->V."""
    table = {"І": "I", "і": "I", "Х": "X", "х": "X", "У": "V", "у": "V"}
    return "".join(table.get(ch, ch) for ch in s).upper()


ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}


@dataclass
class Citation:
    raw: str
    volume: Optional[int]
    page: Optional[int]
    headword: Optional[str]


def parse_citation(text: str, headword: Optional[str] = None) -> Optional[Citation]:
    """Витягує (том, сторінка) з рядка на кшталт «т. IV, с. 293»."""
    if not text:
        return None
    m = CITATION_RE.search(text)
    if not m:
        return None
    vol_raw, page = _normalize_roman(m.group(1)), int(m.group(2))
    volume = ROMAN.get(vol_raw) or (int(vol_raw) if vol_raw.isdigit() else None)
    return Citation(raw=m.group(0), volume=volume, page=page, headword=headword)


# Слово, на яке посилається твердження: у лапках, у дужках, або після
# «модель / за моделлю / за зразком / на зразок / моделі».
HEADWORD_PATTERNS = [
    r"[«'\"]([А-ЯЄІЇҐа-яєіїґ’']+)[»'\"]",
    # «модель / моделі / моделлю / моделями» — хвіст будь-який, аби корінь був
    r"(?:за\s+)?(?:модел\w{0,4}|зразк(?:ом|у)|на\s+зразок)\s+([А-ЯЄІЇҐа-яєіїґ’']+)",
    r"\(([А-ЯЄІЇҐа-яєіїґ’']+)[,)]",
    r"давні\s+композити\s+на\s+зразок\s+([А-ЯЄІЇҐа-яєіїґ’']+)",
]


def extract_headword(text: str) -> Optional[str]:
    for pat in HEADWORD_PATTERNS:
        m = re.search(pat, text or "")
        if m:
            w = m.group(1)
            if len(w) >= 3 and w.lower() not in ("грінченко", "словарь", "модель"):
                return w
    return None


def check_volume_consistency(citation: Citation) -> Dict[str, Any]:
    """
    Найдешевша перевірка: чи може слово взагалі бути в заявленому томі.

    Не потребує ані завантаження словника, ані мережі — лише абетки.
    Ловить найгрубіші вигадки одразу.
    """
    if not citation.headword or citation.volume is None:
        return {"verdict": "UNDECIDABLE", "reason": "немає слова або тому"}
    exp = expected_volume(citation.headword)
    if exp is None:
        return {"verdict": "UNDECIDABLE", "reason": "літера поза абеткою"}
    if exp == citation.volume:
        return {"verdict": "PLAUSIBLE", "expected_volume": exp}
    return {
        "verdict": "CONTRADICTED",
        "expected_volume": exp,
        "claimed_volume": citation.volume,
        "reason": (
            f"«{citation.headword}» починається на «{citation.headword[:1].upper()}», "
            f"це том {exp}, а посилання каже том {citation.volume}"
        ),
    }


DDL = """
CREATE TABLE IF NOT EXISTS lexicon_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  editor TEXT,
  published TEXT,
  volumes INTEGER,
  source_url TEXT,
  fetched_at_utc TEXT,
  raw_sha256 TEXT,
  raw_bytes INTEGER,
  media_type TEXT,
  has_text_layer INTEGER DEFAULT 0,
  rights TEXT NOT NULL,
  rights_basis TEXT,
  acquisition_class TEXT NOT NULL
    CHECK (acquisition_class IN ('verified','unsourced','absent')),
  note TEXT
);

CREATE TABLE IF NOT EXISTS lexicon_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  headword TEXT NOT NULL,
  volume INTEGER,
  page INTEGER,
  artifact_sha256 TEXT,
  byte_start INTEGER,
  byte_len INTEGER,
  window_sha256 TEXT,
  verified_at_utc TEXT,
  FOREIGN KEY (source_id) REFERENCES lexicon_sources(source_id),
  UNIQUE (source_id, headword, volume, page)
);

CREATE INDEX IF NOT EXISTS idx_lexicon_headword
  ON lexicon_entries(headword, source_id);

CREATE TABLE IF NOT EXISTS grinchenko_claim_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attestation_id INTEGER,
  proposed_ukr_term TEXT,
  claim_text TEXT NOT NULL,
  claimed_headword TEXT,
  claimed_volume INTEGER,
  claimed_page INTEGER,
  verdict TEXT NOT NULL
    CHECK (verdict IN ('CONFIRMED','CONTRADICTED','NOT_FOUND','UNDECIDABLE')),
  evidence TEXT,
  checked_at_utc TEXT
);
"""


def init_schema(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    con.executescript(DDL)
    con.commit()
    con.close()


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
