"""
Core data models for AutoSciFi & Lexicon («Космослов»).
Defines entities for Authors, Works, Cult Index, Sci-Fi Terms, and Research Cycles.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Author(BaseModel):
    id: Optional[int] = None
    slug: str
    name_orig: str
    name_ukr: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    country: str
    primary_language: str = "en"
    cult_tier: int = 1  # 1: Titan/Trope-Maker, 2: Master/Visionary, 3: Cult Pioneer
    cult_score: float = 0.0
    awards_summary: Optional[str] = None
    trope_influence: Optional[str] = None
    bio_summary: Optional[str] = None


class Work(BaseModel):
    id: Optional[int] = None
    slug: str
    author_id: int
    title_orig: str
    title_ukr: str
    year: int
    original_lang: str = "en"
    form: str = "Novel"  # Novel, Novella, Short Story, Cycle, Play
    subgenres: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    canon_inclusions: List[str] = Field(default_factory=list)  # e.g., SF Masterworks, NPR Top 100, Locus Poll
    cult_score: float = 0.0
    synopsis: Optional[str] = None
    has_full_text: bool = False
    text_path: Optional[str] = None
    word_count: int = 0
    research_status: str = "pending"  # pending, in_progress, analyzed, verified


class NeologismInterpretation(BaseModel):
    variant: str
    morphemes: str  # e.g., "мить (корінь) + є (сполучний) + вість (основа) + ник (суфікс)"
    grinchenko_model: str  # e.g., "за моделлю вісник, провісник (Грінченко І, 285)"
    semantic_nuance: str  # Чому саме так передає зміст


class SciFiTerm(BaseModel):
    id: Optional[int] = None
    term_orig: str
    ipa: Optional[str] = None
    work_id: int
    author_id: int
    first_attestation_year: Optional[int] = None
    original_context: Optional[str] = None  # Quotes live as byte-coordinates in attestations table
    context_source_locator: Optional[str] = None  # Розділ, сторінка або сцена
    concept_category: str = "Фантастичний концепт"  # e.g., "Технологія зв'язку", "Кібернетика"
    scientific_definition: str = ""  # Академічна дефініція у всесвіті твору
    ukr_traditional: Optional[str] = None  # Існуючий традиційний переклад (якщо був)
    ukr_grinchenko_neologisms: List[NeologismInterpretation] = Field(default_factory=list)
    morphological_rationale: Optional[str] = None  # Академічне обґрунтування за питомим словотвором
    ukr_translated_context: Optional[str] = None  # Художній переклад цитати українською з новим терміном
    verification_score: float = 0.0  # Оцінка якості (0.0 - 1.0)
    status: str = "verified"  # candidate, verified, rejected


class ResearchCycle(BaseModel):
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    target_work_id: int
    target_work_title: str
    hypothesis: str
    llm_model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    terms_discovered: int = 0
    loss_or_quality_score: float = 0.0
    status: str = "committed"  # committed, rolled_back, failed
    notes: Optional[str] = None
