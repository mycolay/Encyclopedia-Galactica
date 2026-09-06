"""
Acceptance tests for T13: Morphological Validator (COSMOSLOV_TZ_EXECUTOR_V2)
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.lexicography.grinchenko_engine import GrinchenkoEngine

def test_rejects_junk():
    for j in ['', '12345', 'asdfgh', 'qwerty']:
        res = GrinchenkoEngine.evaluate_ukrainian_neologism(j, '')
        assert res['is_acceptable'] is False, f"Expected False for junk '{j}', got {res}"
    print("test_rejects_junk: OK")

def test_accepts_real():
    for g in ['мислитель', 'вчитель', 'Миттєвісник', 'провісник']:
        res = GrinchenkoEngine.evaluate_ukrainian_neologism(g, '')
        assert res['is_acceptable'] is True, f"Expected True for real word '{g}', got {res}"
    print("test_accepts_real: OK")

if __name__ == "__main__":
    test_rejects_junk()
    test_accepts_real()
    print("\nT13 ACCEPTANCE TESTS PASSED!")
