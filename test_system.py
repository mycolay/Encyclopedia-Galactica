"""
Automated Test Suite for AutoSciFi & Lexicon («Космослов»).
Verifies database integrity, cult ranker, Grinchenko morphological engine,
corpus context extraction, Karpathy Critic, and LLM connectivity.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path and UTF-8 is configured
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import pytest
from core.db import DatabaseManager
from core.models import SciFiTerm, NeologismInterpretation
from modules.catalog.ranker import CultRanker
from modules.corpus.manager import CorpusManager
from modules.lexicography.grinchenko_engine import GrinchenkoEngine
from modules.autoresearch.evaluator import KarpathyCritic
from modules.autoresearch.llm_client import LocalLLMClient


def test_database_and_stats():
    """Verify database connection, tables, and statistics."""
    db = DatabaseManager()
    stats = db.get_stats()
    assert stats["authors_count"] >= 10, "Authors count should be at least 10"
    assert stats["works_count"] >= 10, "Works count should be at least 10"
    assert stats["terms_count"] >= 5, "Initial canonical terms count should be at least 5"


def test_fts5_fulltext_search():
    """Verify full-text search retrieves indexed terms."""
    db = DatabaseManager()
    results = db.get_terms(search="robot")
    assert len(results) > 0, "FTS5 should match 'robot'"
    assert results[0]["term_orig"].lower() == "robot"

    ansible_res = db.get_terms(search="ansible")
    assert len(ansible_res) > 0, "FTS5 should match 'ansible'"


def test_cult_ranker_formula():
    """Verify cult index calculations for foundational and award-winning works."""
    # Hugo + Nebula winner with full canon inclusion should achieve an elite score >= 95.0
    score_dune = CultRanker.calculate_work_cult_score(
        year=1965,
        awards=["Hugo Winner", "Nebula Winner"],
        canon_inclusions=["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best", "r/printSF Top Tier"],
        trope_maker=True
    )
    assert score_dune >= 95.0, f"Dune cult score should be >= 95.0, got {score_dune}"

    # Early proto-SF classic with no contemporary awards should benefit from historic multiplier
    score_proto = CultRanker.calculate_work_cult_score(
        year=1920,
        awards=[],
        canon_inclusions=["SF Masterworks", "Locus All-Time Best", "Porges Century Canon"],
        trope_maker=True
    )
    assert score_proto >= 90.0, f"Proto-SF trope maker should be >= 90.0, got {score_proto}"


def test_grinchenko_morphological_critique():
    """Verify Ukrainian morphological analyzer detects Russianisms and approves authentic forms."""
    # Authentic form with -ник and пра-
    res_good = GrinchenkoEngine.evaluate_ukrainian_neologism(
        variant="Правісник",
        rationale="пра- (давній префікс) + вість + ник (суфікс приладу чи вісника)"
    )
    assert res_good["is_acceptable"] is True
    assert res_good["score"] >= 0.85

    # Bad form containing Russianism marker
    res_bad = GrinchenkoEngine.evaluate_ukrainian_neologism(
        variant="Включатель",
        rationale="включать прибор"
    )
    assert res_bad["is_acceptable"] is False
    assert res_bad["score"] < 0.60


def test_corpus_context_search():
    """Verify corpus text storage and exact term context extraction."""
    mgr = CorpusManager()
    sample_text = (
        "The League sent its ships into the void. To communicate across forty light-years, "
        "they relied on the ansible, which transmitted information instantaneously."
    )
    mgr.store_text("test-author", "test-work", sample_text)
    loaded = mgr.load_text("test-author", "test-work")
    assert loaded == sample_text

    contexts = mgr.search_term_context(sample_text, "ansible", window_chars=50)
    assert len(contexts) == 1
    assert "ansible" in contexts[0]["exact_match"].lower()


def test_karpathy_critic_evaluation():
    """Verify Karpathy Critic score on complete and incomplete candidates."""
    valid_candidate = {
        "term_orig": "ansible",
        "scientific_definition": "Прилад для миттєвого підпросторового зв'язку без обмеження швидкістю світла.",
        "original_context": "We use the ansible to call across fifty light-years.",
        "ukr_grinchenko_neologisms": [
            {
                "variant": "Миттєвісник",
                "morphemes": "мить + є + вість + ник",
                "grinchenko_model": "Словарь Грінченка, т. І, с. 240 (вісник)",
                "semantic_nuance": "Прилад, що передає вістку тієї самої миті"
            }
        ],
        "morphological_rationale": "Утворено від основи 'вість' та 'мить' за моделлю вісник, провісник.",
        "ukr_translated_context": "Ми використовуємо миттєвісник, щоб кликати за п'ятдесят світлових років."
    }
    source_text = "We use the ansible to call across fifty light-years without delay."
    score, passed, details = KarpathyCritic.evaluate_candidate(valid_candidate, source_text)

    assert passed is True
    assert score >= 0.85, f"Valid candidate score should be >= 0.85, got {score}"

    # Invalid candidate (missing fields, hallucinated term not in context)
    invalid_candidate = {
        "term_orig": "quantum_flux",
        "scientific_definition": "Too short",
        "original_context": "Nothing here",
        "ukr_grinchenko_neologisms": []
    }
    inv_score, inv_passed, inv_details = KarpathyCritic.evaluate_candidate(invalid_candidate, source_text)
    assert inv_passed is False
    assert inv_score < 0.60


def test_nas_llm_ready_packaging():
    """Verify that CorpusManager packages texts into full_text.md, manifest.json, and chapters."""
    mgr = CorpusManager()
    sample_novel = (
        "CHAPTER I. THE BEGINNING\n\n"
        "This is the first chapter of the great cosmic adventure.\n"
        "The stars were burning in the silence of space.\n\n"
        "CHAPTER II. THE CONTACT\n\n"
        "This is the second chapter where the alien signal was heard.\n"
    )
    res = mgr.package_llm_ready_work(
        author_slug="test-author-nas",
        work_slug="test-cosmic-book",
        text=sample_novel,
        metadata={"title": "Test Cosmic Book", "year": 2026}
    )
    assert Path(res["full_text_path"]).exists()
    assert Path(res["manifest_path"]).exists()
    assert res["chapters_count"] == 2

    # Load chapter 1
    ch1 = mgr.load_chapter("test-author-nas", "test-cosmic-book", 1)
    assert ch1 is not None
    assert "CHAPTER I" in ch1

    # Load manifest
    manifest = mgr.load_manifest("test-author-nas", "test-cosmic-book")
    assert manifest is not None
    assert manifest["work_slug"] == "test-cosmic-book"
    assert len(manifest["chapters"]) == 2


def test_harvester_gutenberg_cleaning():
    """Verify Gutenberg header and footer cleaning."""
    from modules.corpus.harvester import PublicDomainHarvester
    db = DatabaseManager()
    mgr = CorpusManager()
    harvester = PublicDomainHarvester(mgr, db)

    raw_gutenberg = (
        "*** START OF THE PROJECT GUTENBERG EBOOK FRANKENSTEIN ***\n\n"
        "Letter 1\nTo Mrs. Saville, England.\nSt. Petersburgh, Dec. 11th, 17--.\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK FRANKENSTEIN ***"
    )
    cleaned = harvester.clean_gutenberg_text(raw_gutenberg)
    assert "*** START" not in cleaned
    assert "*** END" not in cleaned
    assert "Letter 1" in cleaned


if __name__ == "__main__":
    pytest.main(["-v", __file__])
