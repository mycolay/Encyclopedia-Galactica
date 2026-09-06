"""
Structural Zones Module (Т10 - COSMOSLOV_TZ_EXECUTOR_V2)
Determines structural zones (front_matter, toc, body, back_matter) to isolate narrative attestations from service metadata.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

def detect_zones(data: bytes) -> List[Dict[str, Any]]:
    """
    Deterministically computes byte ranges for structural zones in a text file.
    Zones:
    - front_matter: 0 up to start of TOC or narrative body (e.g. YAML header, title, preface)
    - toc: table of contents section
    - body: main narrative text (the only zone eligible for historical dating)
    - back_matter: postscripts, appendices, or footers
    """
    total_len = len(data)

    # 1. Look for TOC header
    toc_pattern = re.compile(rb'\b(?:CONTENTS|TABLE\s+OF\s+CONTENTS|INDEX)\b', re.IGNORECASE)
    toc_match = toc_pattern.search(data)

    # 2. Look for Chapter 1 / Body start
    # Matches: CHAPTER I, CHAPTER 1, BOOK I, PART I, I.\s+..., or CHAPTER ONE
    ch1_patterns = [
        rb'(?:\r?\n|^)\s*(?:CHAPTER\s+(?:I|1|ONE)\b|BOOK\s+(?:I|1|ONE)\b|PART\s+(?:I|1|ONE)\b)',
        rb'(?:\r?\n|^)\s*(?:I\.\s+[A-Z]|I\s*\r?\n\s*[A-Z])'
    ]
    ch1_pos = None

    # Search for chapter 1 start after TOC if TOC exists, or from start
    search_start = toc_match.end() if toc_match else 0
    for pat in ch1_patterns:
        m = re.search(pat, data[search_start:], re.IGNORECASE)
        if m:
            ch1_pos = search_start + m.start()
            break

    if ch1_pos is None:
        # Fallback: if frontmatter is present (---), body starts after second ---
        if data.startswith(b'---'):
            parts = data.split(b'---', 2)
            if len(parts) >= 3:
                ch1_pos = len(parts[0]) + len(parts[1]) + 6
        if ch1_pos is None:
            ch1_pos = 0

    # 3. Look for End of Body
    end_pattern = re.compile(rb'(?:\r?\n|^)\s*(?:THE\s+END|FINIS)\b', re.IGNORECASE)
    end_match = end_pattern.search(data[ch1_pos:])
    if end_match:
        body_end = ch1_pos + end_match.end()
    else:
        # Check for Gutenberg end banner
        pg_end = re.search(rb'\*\*\*\s*END\s+OF\s+TH(?:E|IS)\s+PROJECT\s+GUTENBERG', data, re.IGNORECASE)
        if pg_end:
            body_end = pg_end.start()
        else:
            body_end = total_len

    zones = []

    if toc_match and ch1_pos > toc_match.start():
        # front_matter -> toc -> body -> back_matter
        front_end = toc_match.start()
        toc_start = toc_match.start()
        toc_end = ch1_pos

        zones.append({"kind": "front_matter", "byte_start": 0, "byte_end": front_end})
        zones.append({"kind": "toc", "byte_start": toc_start, "byte_end": toc_end})
        zones.append({"kind": "body", "byte_start": toc_end, "byte_end": body_end})
        zones.append({"kind": "back_matter", "byte_start": body_end, "byte_end": total_len})
    else:
        # front_matter -> body -> back_matter
        zones.append({"kind": "front_matter", "byte_start": 0, "byte_end": ch1_pos})
        zones.append({"kind": "body", "byte_start": ch1_pos, "byte_end": body_end})
        zones.append({"kind": "back_matter", "byte_start": body_end, "byte_end": total_len})

    return zones

def get_zone_for_byte(zones_data: Dict[str, Any], byte_offset: int) -> str:
    """Returns the kind of zone ('front_matter', 'toc', 'body', 'back_matter') for a given byte offset."""
    zones = zones_data.get("zones", [])
    for z in zones:
        if z["byte_start"] <= byte_offset < z["byte_end"]:
            return z["kind"]
    # Fallback to last zone or body
    return "body"

def generate_zones_for_file(file_path: str) -> Dict[str, Any]:
    """Generates and writes zones.json alongside the target text file."""
    p = Path(file_path)
    data = open(p, "rb").read()
    zones = detect_zones(data)
    result = {"zones": zones, "file": p.name, "total_bytes": len(data)}
    out_path = p.parent / "zones.json"
    with open(out_path, "wb") as f:
        f.write(json.dumps(result, indent=2).encode("utf-8"))
    return result

def generate_all_library_zones(library_root: str = "K:/scifi_library"):
    """Scans all works in the library and ensures zones.json exists."""
    count = 0
    for root, _, files in os.walk(library_root):
        if "full_text.md" in files:
            target = os.path.join(root, "full_text.md")
            generate_zones_for_file(target)
            count += 1
    return count

if __name__ == "__main__":
    n = generate_all_library_zones()
    print(f"Generated zones.json for {n} library works.")
