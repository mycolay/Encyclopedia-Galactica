"""
The Karpathy AutoResearch Loop for Science Fiction Lexicography.
Autonomous cycle: Propose -> Execute (LLM) -> Synthesize -> Evaluate -> Commit/Rollback.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from core.db import DatabaseManager
from core.models import SciFiTerm, ResearchCycle, NeologismInterpretation
from modules.corpus.manager import CorpusManager
from modules.autoresearch.llm_client import LocalLLMClient
from modules.autoresearch.evaluator import KarpathyCritic
from modules.lexicography.dictionary_exporter import DictionaryExporter

logger = logging.getLogger("AutoResearch.Loop")


class AutoResearchRunner:
    def __init__(
        self,
        db: DatabaseManager,
        corpus_mgr: CorpusManager,
        llm_client: LocalLLMClient,
        on_cycle_complete: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.db = db
        self.corpus_mgr = corpus_mgr
        self.llm_client = llm_client
        self.exporter = DictionaryExporter(db)
        self.on_cycle_complete = on_cycle_complete
        self.is_running = False

    def get_next_work_target(self) -> Optional[Dict[str, Any]]:
        """Selects the next pending or in-progress cult work from the catalog."""
        works = self.db.get_works(limit=50, order_by="has_full_text DESC, cult_score DESC")
        for w in works:
            if w.get("research_status") in ("pending", "in_progress") and w.get("has_full_text"):
                return w
        # Fallback to any top work even if pending text download
        for w in works:
            if w.get("research_status") == "pending":
                return w
        return None

    def run_single_cycle(self, target_work: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes one full Karpathy Loop iteration.
        """
        if not target_work:
            target_work = self.get_next_work_target()

        if not target_work:
            return {"status": "idle", "message": "Всі доступні твори вже опрацьовано!"}

        work_id = target_work["id"]
        work_title = target_work["title_orig"]
        author_id = target_work["author_id"]
        author_name = target_work["author_name_orig"]
        author_ukr = target_work["author_name_ukr"]
        year = target_work["year"]
        author_slug = target_work.get("author_slug", "")
        work_slug = target_work.get("slug", "")

        hypothesis = (
            f"Аналіз тексту «{work_title}» ({author_name}, {year}) для виявлення "
            f"ключових авторських термінів та їхня наукова деривація за словником Грінченка."
        )

        # 1. Fetch text from corpus
        raw_text = None
        if target_work.get("text_path"):
            try:
                with open(target_work["text_path"], "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
            except Exception:
                pass

        if not raw_text:
            raw_text = self.corpus_mgr.load_text(author_slug, work_slug)

        if not raw_text:
            # If no local text, use canonical synopsis and historical knowledge
            raw_text = f"{target_work.get('synopsis', '')}\nAwards: {target_work.get('awards_json', '')}"

        # Truncate text chunk if too long for prompt speed (top 1800 characters)
        text_chunk = raw_text[:1800]

        logger.info(f"Запуск циклу дослідження для: {work_title} ({author_name})")

        # 2. Call Local LLM on RTX 3090
        try:
            llm_result = self.llm_client.analyze_sci_fi_text(
                author_name=author_name,
                work_title=work_title,
                year=year,
                excerpt_text=text_chunk
            )
            candidate = llm_result.get("json", {})
            prompt_tokens = llm_result.get("prompt_eval_count", 0)
            completion_tokens = llm_result.get("eval_count", 0)
        except Exception as e:
            logger.error(f"Помилка виклику LLM: {e}")
            cycle = ResearchCycle(
                target_work_id=work_id,
                target_work_title=work_title,
                hypothesis=hypothesis,
                llm_model=self.llm_client.model_name,
                status="failed",
                notes=f"Помилка LLM: {str(e)}"
            )
            self.db.insert_cycle(cycle)
            return {"status": "error", "error": str(e)}

        # 3. Evaluate candidate with Karpathy Critic
        score, passed, eval_details = KarpathyCritic.evaluate_candidate(candidate, text_chunk)

        # 4. Commit or Rollback
        if passed:
            # Build and insert SciFiTerm
            neologisms = [
                NeologismInterpretation(**n) if isinstance(n, dict) else n
                for n in candidate.get("ukr_grinchenko_neologisms", [])
            ]

            term = SciFiTerm(
                term_orig=candidate.get("term_orig", "Невідомо"),
                ipa=candidate.get("ipa"),
                work_id=work_id,
                author_id=author_id,
                first_attestation_year=year,
                original_context=candidate.get("original_context", ""),
                context_source_locator=candidate.get("context_source_locator"),
                concept_category=candidate.get("concept_category", "Фантастичний концепт"),
                scientific_definition=candidate.get("scientific_definition", ""),
                ukr_traditional=candidate.get("ukr_traditional"),
                ukr_grinchenko_neologisms=neologisms,
                morphological_rationale=candidate.get("morphological_rationale", ""),
                ukr_translated_context=candidate.get("ukr_translated_context", ""),
                verification_score=score,
                status="verified"
            )
            term_id = self.db.insert_term(term)

            # Update work status
            with self.db.get_connection() as conn:
                conn.execute("UPDATE works SET research_status = 'analyzed' WHERE id = ?", (work_id,))
                conn.commit()

            # Record committed cycle
            cycle = ResearchCycle(
                target_work_id=work_id,
                target_work_title=work_title,
                hypothesis=hypothesis,
                llm_model=self.llm_client.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                terms_discovered=1,
                loss_or_quality_score=score,
                status="committed",
                notes=f"Термін успішно зафіксовано: {candidate.get('term_orig')} (Оцінка: {score})"
            )
            self.db.insert_cycle(cycle)

            # Refresh Markdown export
            self.exporter.export_markdown()

            res = {
                "status": "committed",
                "term": candidate.get("term_orig"),
                "score": score,
                "work": work_title,
                "author": author_name,
                "eval_details": eval_details
            }
        else:
            # Rollback / log rejection
            cycle = ResearchCycle(
                target_work_id=work_id,
                target_work_title=work_title,
                hypothesis=hypothesis,
                llm_model=self.llm_client.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                terms_discovered=0,
                loss_or_quality_score=score,
                status="rolled_back",
                notes=f"Відхилено критиком (Оцінка: {score} < {KarpathyCritic.ACCEPTANCE_THRESHOLD}). Зауваження: {'; '.join(eval_details.get('penalties', []))}"
            )
            self.db.insert_cycle(cycle)

            res = {
                "status": "rolled_back",
                "term": candidate.get("term_orig"),
                "score": score,
                "work": work_title,
                "eval_details": eval_details
            }

        if self.on_cycle_complete:
            self.on_cycle_complete(res)

        return res
