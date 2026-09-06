"""
System Initializer for AutoSciFi & Lexicon («Космослов»).
Populates database with cult authors, masterpieces, canonical texts,
canonical Grinchenko neologisms, and compiles initial Markdown dictionary.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.db import DatabaseManager
from core.models import SciFiTerm, NeologismInterpretation
from modules.catalog.seed_data import seed_database
from modules.corpus.manager import CorpusManager
from modules.corpus.seed_corpus import populate_seed_corpus
from modules.lexicography.grinchenko_engine import GrinchenkoEngine
from modules.lexicography.dictionary_exporter import DictionaryExporter


def initialize():
    print("=" * 60)
    print("  ІНІЦІАЛІЗАЦІЯ СИСТЕМИ «КОСМОСЛОВ» (AUTOSCIFI & LEXICON)")
    print("=" * 60)

    db = DatabaseManager()
    corpus_mgr = CorpusManager()

    # 1. Seed Authors and Works
    print("[1/5] Завантаження канонічного каталогу авторів та творів...")
    seed_database(db)

    # 2. Seed Texts into Corpus Repository
    print("[2/5] Завантаження канонічних текстів мовою оригіналу в корпус...")
    populate_seed_corpus(db, corpus_mgr)

    # 3. Seed Canonical Lexicographical Terms
    print("[3/5] Внесення основоположних термінів та аналізу Грінченка в базу...")
    seed_terms = GrinchenkoEngine.get_seed_terms()

    # Build work & author mapping
    with db.get_connection() as conn:
        works_rows = conn.execute("SELECT id, slug, author_id FROM works").fetchall()
        work_map = {row["slug"]: (row["id"], row["author_id"]) for row in works_rows}

    for item in seed_terms:
        w_slug = item["work_slug"]
        if w_slug in work_map:
            w_id, a_id = work_map[w_slug]
            neologisms = [
                NeologismInterpretation(**n) for n in item["ukr_grinchenko_neologisms"]
            ]
            term = SciFiTerm(
                term_orig=item["term_orig"],
                ipa=item["ipa"],
                work_id=w_id,
                author_id=a_id,
                first_attestation_year=item["first_attestation_year"],
                original_context=item["original_context"],
                context_source_locator=item["context_source_locator"],
                concept_category=item["concept_category"],
                scientific_definition=item["scientific_definition"],
                ukr_traditional=item["ukr_traditional"],
                ukr_grinchenko_neologisms=neologisms,
                morphological_rationale=item["morphological_rationale"],
                ukr_translated_context=item["ukr_translated_context"],
                verification_score=item["verification_score"],
                status="verified"
            )
            db.insert_term(term)

    # 4. Generate initial Academic Markdown Dictionary
    print("[4/5] Експорт академічного зводу словника в docs/SCI_FI_LEXICON.md...")
    exporter = DictionaryExporter(db)
    doc_path = exporter.export_markdown()
    print(f"      Словник згенеровано: {doc_path}")

    # 5. Summary Stats
    stats = db.get_stats()
    print("[5/5] Підсумок бази даних:")
    print(f"      Авторів у каталозі:       {stats['authors_count']}")
    print(f"      Творів у каталозі:         {stats['works_count']}")
    print(f"      Повних текстів у корпусі:  {stats['full_texts_count']}")
    print(f"      Наукових термінів у базі:  {stats['terms_count']}")
    print("=" * 60)
    print("Ініціалізацію успішно завершено!")


if __name__ == "__main__":
    initialize()
