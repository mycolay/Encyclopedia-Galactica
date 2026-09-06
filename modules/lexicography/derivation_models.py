"""
Пошук СПРАВЖНІХ словотвірних моделей у Грінченка.

Навіщо.
Дев'ять дериваційних обґрунтувань у проєкті посилалися на слова, яких у
словнику немає: трудник, ділороб, безчасний, скоропис, віщунство,
мовознавство. Модель їх вигадала разом із номером тому. Замість вигадувати
знову, тут шукаються реально засвідчені слова з тим самим словотвірним
типом — так, як робить лексикограф.

Кожна знайдена модель має байтову координату в запечатаному артефакті,
тобто перевіряється тим самим способом, що й цитати з творів.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

INDEX_PATH = Path("K:/scifi_library/lexicons/hrinchenko-1907-1909/headwords.json")
ARTIFACT_PATH = Path("K:/scifi_library/lexicons/hrinchenko-1907-1909/hrinchenko.txt")

VOLUME_RANGES = [(1, "А", "Ж"), (2, "З", "Н"), (3, "О", "П"), (4, "Р", "Я")]
UKR_ALPHABET = "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ"


def strip_accents(s: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )


def volume_of(headword: str) -> Optional[int]:
    first = strip_accents(headword).strip().upper()[:1]
    first = {"Ъ": "", "Ы": "И", "Э": "Е"}.get(first, first)
    if first not in UKR_ALPHABET:
        return None
    idx = UKR_ALPHABET.index(first)
    for vol, lo, hi in VOLUME_RANGES:
        if UKR_ALPHABET.index(lo) <= idx <= UKR_ALPHABET.index(hi):
            return vol
    return None


@dataclass
class DerivationModel:
    headword: str
    volume: Optional[int]
    byte_start: int
    byte_len: int
    gloss: str

    def as_citation(self) -> str:
        return f"«{self.headword}» (Грінченко, том {self.volume})"


class HrinchenkoIndex:
    """Покажчик реєстрових слів із перевіркою версії збірки."""

    EXPECTED_INDEXER = "build_hrinchenko_index.v2"

    def __init__(self, index_path: Path = INDEX_PATH, artifact_path: Path = ARTIFACT_PATH):
        raw = json.loads(index_path.read_text(encoding="utf-8"))
        if raw.get("indexer_version") != self.EXPECTED_INDEXER:
            raise RuntimeError(
                f"покажчик зібрано версією {raw.get('indexer_version')!r}, "
                f"потрібна {self.EXPECTED_INDEXER!r} — перебудуйте"
            )
        self.artifact_sha256: str = raw["artifact_sha256"]
        self.entries: List[Dict[str, Any]] = raw["entries"]
        self.data: bytes = artifact_path.read_bytes()
        self._by_norm: Dict[str, List[Dict[str, Any]]] = {}
        for e in self.entries:
            self._by_norm.setdefault(strip_accents(e["headword"]).lower(), []).append(e)

    def __len__(self) -> int:
        return len(self.entries)

    def exists(self, word: str) -> bool:
        return strip_accents(word).lower() in self._by_norm

    def _gloss(self, entry: Dict[str, Any], width: int = 90) -> str:
        line = self.data[entry["byte_start"]: entry["byte_start"] + entry["byte_len"]]
        return " ".join(line.decode("utf-8", errors="replace").split())[:width]

    def get(self, word: str) -> Optional[DerivationModel]:
        found = self._by_norm.get(strip_accents(word).lower())
        if not found:
            return None
        e = found[0]
        return DerivationModel(
            headword=e["headword"],
            volume=volume_of(e["headword"]),
            byte_start=e["byte_start"],
            byte_len=e["byte_len"],
            gloss=self._gloss(e),
        )

    def find_by_pattern(
        self,
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        contains: Optional[str] = None,
        min_len: int = 4,
        limit: int = 25,
    ) -> List[DerivationModel]:
        """
        Реально засвідчені слова з потрібним афіксом.

        Це заміна вигадуванню: якщо потрібна модель на «-ник», беремо ті
        «-ник», що справді є у словнику, з координатою кожного.
        """
        out: List[DerivationModel] = []
        for e in self.entries:
            hw = strip_accents(e["headword"]).lower()
            if len(hw) < min_len:
                continue
            if suffix and not hw.endswith(suffix.lower()):
                continue
            if prefix and not hw.startswith(prefix.lower()):
                continue
            if contains and contains.lower() not in hw:
                continue
            out.append(
                DerivationModel(
                    headword=e["headword"],
                    volume=volume_of(e["headword"]),
                    byte_start=e["byte_start"],
                    byte_len=e["byte_len"],
                    gloss=self._gloss(e),
                )
            )
            if len(out) >= limit:
                break
        return out

    def verify_model(self, word: str) -> Dict[str, Any]:
        """
        Чи можна на це слово посилатися. Відповідь бінарна.
        """
        m = self.get(word)
        if not m:
            return {"verdict": "ABSENT", "word": word,
                    "evidence": f"«{word}» у Словарі Грінченка не знайдено"}
        at = self.data[m.byte_start: m.byte_start + m.byte_len]
        head_ok = strip_accents(
            at.decode("utf-8", errors="replace")
        ).lower().startswith(strip_accents(m.headword).lower()[:5])
        return {
            "verdict": "ATTESTED" if head_ok else "COORD_MISMATCH",
            "word": m.headword,
            "volume": m.volume,
            "byte_start": m.byte_start,
            "byte_len": m.byte_len,
            "gloss": m.gloss,
            "evidence": m.as_citation(),
        }
