"""
Witness Architecture Implementation (Т9 - COSMOSLOV_TZ_EXECUTOR_V2)
Deterministic byte-offset attestation, cryptographic sealing, and fail-closed verification.
"""

import os
import re
import hashlib
from typing import Optional, List, Dict, Any, Tuple

class WitnessCorrupted(Exception):
    """Raised when an attestation witness fails cryptographic or textual verification."""
    pass

def sha256_bytes(b: bytes) -> str:
    """Computes standard SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(b).hexdigest()

def snap_to_utf8_boundary(data: bytes, pos: int, direction: str = 'backward') -> int:
    """
    Snaps a byte index to the nearest valid UTF-8 character start boundary.
    Prevents splitting multi-byte UTF-8 sequences (Cyrillic, Czech diacritics).
    In UTF-8, continuation bytes match bitmask 10xxxxxx (0x80..0xBF).
    """
    if pos <= 0 or pos >= len(data):
        return max(0, min(pos, len(data)))
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        if direction == 'backward':
            pos -= 1
        else:
            pos += 1
            if pos >= len(data):
                break
    return pos

def find_occurrences(data: bytes, term: str, variants: Optional[List[str]] = None) -> List[Tuple[int, str]]:
    """
    Finds all occurrences of a term and its morphological variants.
    Operates on decoded UTF-8 text to correctly handle Unicode word boundaries
    and casing, then computes exact byte offset.
    Supports multi-word terms across newlines and hyphens (r'[-\s]+').
    Returns [(byte_offset, matched_form), ...].
    """
    text = data.decode('utf-8', errors='replace')
    words = [term] + (variants or [])
    parts = []
    for w in words:
        segments = re.split(r'[-\s]+', w)
        # Нормалізація роздільника (дефіс <-> пробіл <-> розрив рядка) безпечна
        # лише коли ВСІ частини достатньо довгі. Для коротких вона перетворює
        # термін на пастку: «An-a» ловило «an An have» — англійський артикль
        # плюс слово, а не термін Бульвер-Літтона. Тому для термів із частиною
        # коротшою за 3 символи роздільник шукаємо ДОСЛІВНО.
        if all(len(s) >= 3 for s in segments):
            parts.append(r'[-\s]+'.join(re.escape(s) for s in segments))
        else:
            parts.append(re.escape(w))
    # Inflectional tail is BOUNDED.
    #
    # Тут стояло `\w*` (необмежене). Разом із нормалізацією дефіса це давало
    # катастрофічний перебір: терм «An-a» ловив «an anxious», «an atmosphere»,
    # «an automaton» — бо `a` + `\w*` дозволяв дорости на будь-яку довжину.
    # Перевірено 2026-09-06, 1 хибний свідок потрапив у базу.
    #
    # Реальні флексії короткі: morlock+s, Robot+ů, Robot+y, Robot+ech (+3),
    # Thark+s, Selenite+s. Трьох символів досить, семи вже забагато.
    pattern = r'\b(?:' + '|'.join(parts) + r')\w{0,3}\b'
    out = []
    for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.UNICODE):
        # Exact byte offset of match start
        byte_pos = len(text[:m.start()].encode('utf-8'))
        out.append((byte_pos, m.group()))
    return out

def build_witness(
    path: str,
    term: str,
    occurrence_index: int = 0,
    pad: int = 80,
    length: int = 200,
    variants: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Deterministically locates term in a file and returns an exact byte coordinate witness.
    Zero LLM involvement.
    """
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        data = f.read()

    found = find_occurrences(data, term, variants)
    if occurrence_index >= len(found):
        return None

    pos, form = found[occurrence_index]
    start = snap_to_utf8_boundary(data, max(0, pos - pad), 'backward')
    end = snap_to_utf8_boundary(data, min(len(data), start + length), 'forward')
    window = data[start:end]

    return {
        "artifact_sha256": sha256_bytes(data),
        "byte_start": start,
        "byte_len": len(window),
        "window_sha256": sha256_bytes(window),
        "matched_form": form,
        "occurrences_total": len(found),
    }

def verify_witness(w: Dict[str, Any], path: str, term: str = "") -> Tuple[str, str, Optional[str]]:
    """
    Performs 5 strict binary verification checks on a witness:
    1. Artifact SHA256 integrity (no drift)
    2. Exact byte length read
    3. Exact window SHA256 match
    4. Valid UTF-8 decodability
    5. Presence of term in window
    Zero partial scores, zero LLM subjectivity.
    """
    if not os.path.exists(path):
        return ("REJECT", "file_not_found", None)

    with open(path, 'rb') as f:
        data = f.read()

    if sha256_bytes(data) != w.get("artifact_sha256"):
        return ("REJECT", "artifact_drift", None)

    byte_start = w.get("byte_start", 0)
    byte_len = w.get("byte_len", 0)
    window = data[byte_start: byte_start + byte_len]

    if len(window) != byte_len:
        return ("REJECT", "short_read", None)

    if sha256_bytes(window) != w.get("window_sha256"):
        return ("REJECT", "window_mismatch", None)

    try:
        text = window.decode('utf-8')
    except UnicodeDecodeError:
        return ("REJECT", "decode_error", None)

    matched_form = w.get("matched_form")
    if term:
        # Перевірка мусить жити за ТИМИ САМИМИ правилами, що й пошук.
        # Раніше find_occurrences нормалізував дефіси й розриви рядків, а
        # verify_witness робив літеральну перевірку — і свідок «Blazing-World»,
        # що в тексті стоїть як «Blazing-\nworld», відхилявся як term_absent,
        # хоча був знайдений коректно. Дві функції жили за різними правилами.
        term_ok = (
            term.lower() in text.lower()
            or bool(matched_form and matched_form.lower() in text.lower())
            or bool(find_occurrences(text.encode("utf-8"), term))
        )
        if not term_ok:
            return ("REJECT", "term_absent", None)

    return ("ACCEPT", "ok", text)

def render_quote(witness: Dict[str, Any], file_path: str, term: str = "") -> str:
    """
    Reads the exact bytes of a verified witness and returns rendered quote text.
    Raises WitnessCorrupted exception on any integrity failure (fail-closed).
    """
    status, reason, text = verify_witness(witness, file_path, term)
    if status != "ACCEPT":
        raise WitnessCorrupted(f"{reason} @ {file_path}:{witness.get('byte_start')}")
    return text.strip()
