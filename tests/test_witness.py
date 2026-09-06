"""
Acceptance tests for T9: Witness Architecture (COSMOSLOV_TZ_EXECUTOR_V2)
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.corpus.witness import (
    build_witness, verify_witness, render_quote,
    find_occurrences, WitnessCorrupted
)

TM_PATH = "K:/scifi_library/authors/h-g-wells/the-time-machine/full_text.md"

def test_roundtrip():
    w = build_witness(TM_PATH, "Morlock")
    assert w is not None, "Failed to build witness for Morlock in The Time Machine"
    status, reason, text = verify_witness(w, TM_PATH, "Morlock")
    assert status == "ACCEPT", f"Roundtrip failed: {reason}"
    assert "Morlock".lower() in text.lower()

def test_shift_one_byte_rejected():
    w = build_witness(TM_PATH, "Morlock")
    assert w is not None
    w["byte_start"] += 1
    status, reason, text = verify_witness(w, TM_PATH, "Morlock")
    assert status == "REJECT", f"Expected REJECT on 1-byte shift, got {status}"

def test_fake_coordinate_rejected():
    w = build_witness(TM_PATH, "Morlock")
    assert w is not None
    w["byte_start"] = 9_999_999
    status, reason, text = verify_witness(w, TM_PATH, "Morlock")
    assert status == "REJECT", f"Expected REJECT on fake coordinate, got {status}"

def test_plural_and_case_found():
    data = "The Morlock and morlocks and MORLOCK.".encode('utf-8')
    assert len(find_occurrences(data, "morlock")) == 3

def test_czech_inflections_found():
    data = "Roboti pracují. Robotů bylo mnoho. roboty zde.".encode('utf-8')
    assert len(find_occurrences(data, "robot")) == 3

def test_multiword_across_newline():
    assert len(find_occurrences(b"a time\nmachine here", "time machine")) == 1

def test_corrupted_raises():
    w = build_witness(TM_PATH, "Morlock")
    assert w is not None
    w["window_sha256"] = "0" * 64
    try:
        render_quote(w, TM_PATH, "Morlock")
        assert False, "Should have raised WitnessCorrupted"
    except WitnessCorrupted:
        pass

if __name__ == "__main__":
    test_roundtrip()
    print("test_roundtrip: OK")
    test_shift_one_byte_rejected()
    print("test_shift_one_byte_rejected: OK")
    test_fake_coordinate_rejected()
    print("test_fake_coordinate_rejected: OK")
    test_plural_and_case_found()
    print("test_plural_and_case_found: OK")
    test_czech_inflections_found()
    print("test_czech_inflections_found: OK")
    test_multiword_across_newline()
    print("test_multiword_across_newline: OK")
    test_corrupted_raises()
    print("test_corrupted_raises: OK")
    print("\nALL 7 WITNESS TESTS PASSED!")
