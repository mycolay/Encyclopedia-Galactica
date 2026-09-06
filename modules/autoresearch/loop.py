"""
The Karpathy AutoResearch Loop for Science Fiction Lexicography.
Autonomous Inverted Cycle (Т12 - COSMOSLOV_TZ_EXECUTOR_V2):
КРОК 1  ПРОПОЗИЦІЯ   LLM читає шматок (вікно 8000, перекриття 200) і називає лише СПИСОК СЛІВ-КАНДИДАТІВ.
КРОК 2  ЛОКАЛІЗАЦІЯ  Код шукає через find_occurrences() у повному тексті, будує свідка і перевіряє зону 'body'.
КРОК 3  ДЕРИВАЦІЯ    LLM отримує верифіковану справжню цитату і пропонує український відповідник (register='proposed').
"""

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List

from core.db import DatabaseManager
from core.models import SciFiTerm, ResearchCycle, NeologismInterpretation
from modules.corpus.manager import CorpusManager
from modules.corpus.witness import build_witness, verify_witness, render_quote
from modules.corpus.zones import get_zone_for_byte, generate_zones_for_file
from modules.corpus.zones_llm import detect_zones_llm, zone_for_span, save_zones
from modules.autoresearch.llm_client import LocalLLMClient
from modules.lexicography.grinchenko_engine import GrinchenkoEngine
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

    def run_extraction_cycle(self, target_work, queue_path, profile, max_windows=5):
        """Durable extraction stage; candidates await localization and editorial work."""
        from modules.corpus.queue import CorpusQueue
        queue = CorpusQueue(queue_path)
        plan = queue.prepare(target_work['id'], target_work['text_path'], profile)
        return queue.run(plan, self.llm_client, target_work['title_orig'],
                         target_work['author_name_orig'], max_windows=max_windows)

    def get_next_work_target(self) -> Optional[Dict[str, Any]]:
        """Selects the next cult work with full text available on disk."""
        works = self.db.get_works(limit=100, order_by="cult_score DESC")
        for w in works:
            if w.get("has_full_text") and w.get("text_path") and os.path.exists(w["text_path"]):
                if w.get("research_status") in ("pending", "in_progress", "verified"):
                    return w
        return None

    def run_single_cycle(
        self,
        target_work: Optional[Dict[str, Any]] = None,
        window_size: int = 8000,
        overlap: int = 200,
        max_windows: int = 5
    ) -> Dict[str, Any]:
        """
        Executes one full Inverted Karpathy Loop iteration.
        """
        if not target_work:
            target_work = self.get_next_work_target()

        if not target_work:
            return {"status": "idle", "message": "Всі доступні твори з повними текстами вже опрацьовано!"}

        work_id = target_work["id"]
        work_title = target_work["title_orig"]
        author_id = target_work["author_id"]
        author_name = target_work["author_name_orig"]
        year = target_work["year"]
        author_slug = target_work.get("author_slug", "")
        work_slug = target_work.get("slug", "")
        text_path = target_work.get("text_path")

        if not text_path or not os.path.exists(text_path):
            return {"status": "error", "error": f"Файл тексту не знайдено на диску: {text_path}"}

        logger.info(f"Запуск інвертованого циклу дослідження для: {work_title} ({author_name}, {year})")

        # 1. Read full text
        with open(text_path, "rb") as f:
            raw_bytes = f.read()
        full_text = raw_bytes.decode("utf-8", errors="replace")

        # 2. Ensure zones.json exists and load structural zones
        # Пріоритет: збережена карта -> LLM-сегментація з якорями -> евристика.
        # Евристика лишається лише як аварійний запас: вона хибно зараховує
        # титульну сторінку і список дійових осіб до 'body' (перевірено на R.U.R.).
        zones_file = Path(text_path).parent / "zones.json"
        zones_data = None
        if zones_file.exists():
            try:
                with open(zones_file, "r", encoding="utf-8") as f:
                    zones_data = json.load(f)
            except Exception:
                zones_data = None

        if not zones_data or not zones_data.get("zones"):
            llm_zones = detect_zones_llm(text_path, llm=self.llm_client)
            if llm_zones.get("status") == "llm_verified":
                save_zones(text_path, llm_zones)
                zones_data = llm_zones
                logger.info(
                    f"Зони визначено моделлю за якорями ({llm_zones.get('work_kind')}): "
                    f"{llm_zones.get('reasoning')}"
                )
            else:
                logger.warning(
                    f"LLM-сегментація не вдалася ({llm_zones.get('status')}). "
                    f"Аварійний запас: евристика. Свідки з цього твору потребують "
                    f"ручного підтвердження зон."
                )
                zones_data = generate_zones_for_file(text_path)
                zones_data["zone_source"] = "heuristic_fallback"

        # 3. Load already attested terms for this work
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT LOWER(term_orig) FROM attestations WHERE work_id = ? AND register = 'attested'",
                (work_id,)
            ).fetchall()
            existing_attested = {r[0].strip() for r in rows if r[0]}

        # 4. Determine body start offset to scan narrative text
        body_start = 0
        for z in zones_data.get("zones", []):
            if z.get("kind") == "body":
                body_start = z.get("byte_start", 0)
                break

        # Generate windows (8000 chars with 200 overlap) starting from narrative body
        step = max(100, window_size - overlap)
        windows = []
        for i in range(body_start, len(full_text), step):
            chunk = full_text[i:i + window_size]
            if len(chunk.strip()) > 200:
                windows.append((i, chunk))

        if not windows:
            return {"status": "error", "error": f"Текст твору «{work_title}» порожній."}

        # Ensure author_slug is present
        if not author_slug:
            auth_info = self.db.get_author_by_id(author_id)
            author_slug = auth_info.get("slug", "unknown-author") if auth_info else "unknown-author"

        # 5. Process windows up to max_windows
        for win_idx, (char_offset, chunk_text) in enumerate(windows[:max_windows]):
            logger.info(f"Вікно {win_idx + 1}/{min(len(windows), max_windows)} (зсув символів {char_offset})")

            # --- КРОК 1: ПРОПОЗИЦІЯ (LLM) ---
            try:
                candidates = self.llm_client.propose_candidates(
                    excerpt_text=chunk_text,
                    work_title=work_title,
                    author_name=author_name
                )
            except Exception as e:
                logger.error(f"Помилка моделі на Кроці 1: {e}")
                cycle = ResearchCycle(
                    target_work_id=work_id,
                    target_work_title=work_title,
                    hypothesis=f"Пропозиція термінів для «{work_title}»",
                    llm_model=self.llm_client.model_name,
                    status="failed",
                    notes=f"Помилка propose_candidates: {e}"
                )
                self.db.insert_cycle(cycle)
                return {"status": "error", "error": str(e)}

            if not candidates:
                logger.info("Модель не виділила кандидатів у цьому вікні, продовжуємо...")
                continue

            logger.info(f"Кандидати від моделі: {candidates}")

            # Filter candidates: non-empty, not already attested, length > 2
            valid_cands = []
            for c in candidates:
                c_clean = c.strip().strip("'\"`.,:;!?")
                if len(c_clean) > 2 and c_clean.lower() not in existing_attested:
                    valid_cands.append(c_clean)

            if not valid_cands:
                continue

            # --- КРОК 2: ЛОКАЛІЗАЦІЯ (КОД, БЕЗ LLM) ---
            from modules.corpus.witness import find_occurrences
            for cand in valid_cands:
                # Search all occurrences in authentic text and locate first one in body zone
                found_occ = find_occurrences(raw_bytes, cand)
                if not found_occ:
                    logger.info(f"Кандидата '{cand}' не знайдено в тексті (галюцинація LLM відкинута).")
                    continue

                witness = None
                zone = None
                for occ_idx, (pos, form) in enumerate(found_occ):
                    # Зона перевіряється для ВСЬОГО вікна свідка, а не для точки
                    # збігу: вікно тягнеться на pad байтів назад і може перетнути
                    # межу, потрапивши у зміст або титульну сторінку.
                    w = build_witness(text_path, cand, occurrence_index=occ_idx)
                    if not w:
                        continue
                    z = zone_for_span(
                        zones_data, w["byte_start"], w["byte_start"] + w["byte_len"]
                    )
                    if z == "body":
                        witness = w
                        zone = z
                        break
                    logger.debug(
                        f"'{cand}' поз.{pos}: вікно {w['byte_start']}.."
                        f"{w['byte_start'] + w['byte_len']} у зоні {z}, не body — пропуск."
                    )

                if not witness or zone != "body":
                    logger.info(f"Для '{cand}' не знайдено входжень, чиє ВІКНО цілком у зоні 'body'. Відхилено з датування.")
                    continue

                # Verify cryptographic witness integrity
                v_status, v_reason, _ = verify_witness(witness, text_path, cand)
                if v_status != "ACCEPT":
                    logger.warning(f"Свідок для '{cand}' не пройшов перевірку ({v_reason}). Відхилено.")
                    continue

                # Extract verified authentic quote
                try:
                    quote = render_quote(witness, text_path, cand)
                except Exception as ex:
                    logger.warning(f"Не вдалося отримати цитату для '{cand}': {ex}")
                    continue

                # --- КРОК 3: ДЕРИВАЦІЯ (LLM) ---
                logger.info(f"Засвідчено '{cand}' (форма: '{witness['matched_form']}', байт: {witness['byte_start']}). Запуск деривації...")
                try:
                    deriv_resp = self.llm_client.derive_ukrainian_neologism(
                        term=cand,
                        verified_quote=quote,
                        work_title=work_title,
                        author_name=author_name
                    )
                    deriv_json = deriv_resp.get("json", {})
                    prompt_tokens = deriv_resp.get("prompt_eval_count", 0)
                    completion_tokens = deriv_resp.get("eval_count", 0)
                except Exception as ex:
                    logger.error(f"Помилка деривації для '{cand}': {ex}")
                    continue

                proposed_ukr = deriv_json.get("proposed_ukr_term", "").strip()
                grinchenko_root = deriv_json.get("grinchenko_root", "").strip()
                derivation_model = deriv_json.get("derivation_model", "").strip()
                stylistic_note = deriv_json.get("stylistic_note", "").strip()
                scientific_def = deriv_json.get("scientific_definition", "").strip()
                concept_category = deriv_json.get("concept_category", "Фантастичний концепт").strip()

                # Morphological evaluation via GrinchenkoEngine
                eval_res = GrinchenkoEngine.evaluate_ukrainian_neologism(
                    proposed_ukr,
                    f"{stylistic_note} {derivation_model}"
                )
                score = eval_res.get("score", 0.0)
                is_acceptable = eval_res.get("is_acceptable", False)

                hypothesis = (
                    f"Аналіз твору «{work_title}» ({author_name}, {year}): "
                    f"пошук терміна '{cand}' та деривація питомого українського відповідника."
                )

                if not is_acceptable:
                    # Rollback cycle
                    logger.info(f"Відхилено за морфологією: '{proposed_ukr}' (оцінка: {score})")
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
                        notes=f"Відхилено морфологічним фільтром для '{proposed_ukr}': {'; '.join(eval_res.get('issues', []))}"
                    )
                    self.db.insert_cycle(cycle)
                    continue

                # --- COMMIT ---
                logger.info(f"Успішна деривація: '{cand}' -> '{proposed_ukr}' (оцінка: {score}). Фіксація в базі...")

                # 1. Insert or reuse term in terms table
                term_row = self.db.get_term_by_orig(cand)
                if term_row:
                    term_id = term_row["id"]
                else:
                    neologisms = [
                        NeologismInterpretation(
                            variant=proposed_ukr,
                            morphemes=derivation_model or grinchenko_root,
                            grinchenko_model=grinchenko_root or "Словарь Грінченка",
                            semantic_nuance=stylistic_note
                        )
                    ]
                    new_term = SciFiTerm(
                        term_orig=cand,
                        ipa=None,
                        work_id=work_id,
                        author_id=author_id,
                        original_context=None,  # Pure cryptographic witness architecture (zero fake strings)
                        context_source_locator=f"byte {witness['byte_start']}",
                        concept_category=concept_category,
                        scientific_definition=scientific_def,
                        ukr_traditional=None,
                        ukr_grinchenko_neologisms=neologisms,
                        morphological_rationale=f"{stylistic_note} (Модель: {derivation_model})",
                        ukr_translated_context=None,
                        verification_score=score,
                        status="verified"
                    )
                    term_id = self.db.insert_term(new_term)

                now_utc = datetime.utcnow().isoformat()
                cts_urn = f"urn:cts:scifi:{author_slug}.{work_slug}:{witness['byte_start']}+{witness['byte_len']}"

                # 2. Insert verified authentic witness into attestations
                attestation_attested = {
                    "term_id": term_id,
                    "term_orig": cand,
                    "work_id": work_id,
                    "year": year,
                    "register": "attested",
                    "zone": zone,
                    "matched_form": witness["matched_form"],
                    "cts_urn": cts_urn,
                    "artifact_sha256": witness["artifact_sha256"],
                    "byte_start": witness["byte_start"],
                    "byte_len": witness["byte_len"],
                    "window_sha256": witness["window_sha256"],
                    "verified_at_utc": now_utc,
                    "verifier_version": "witness_v2"
                }
                self.db.insert_attestation(attestation_attested)

                # 3. Insert proposed Ukrainian neologism into attestations
                attestation_proposed = {
                    "term_id": term_id,
                    "term_orig": cand,
                    "work_id": work_id,
                    "year": year,
                    "register": "proposed",
                    "proposed_ukr_term": proposed_ukr,
                    "grinchenko_root": grinchenko_root,
                    "derivation_model": derivation_model,
                    "stylistic_note": stylistic_note,
                    "root_attested_in_grinchenko": 0,
                    "proposed_by_model": self.llm_client.model_name,
                    "verified_at_utc": now_utc,
                    "verifier_version": "witness_v2"
                }
                self.db.insert_attestation(attestation_proposed)

                # 4. Insert committed research cycle
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
                    notes=(
                        f"Термін успішно зафіксовано: '{cand}' "
                        f"(форма: '{witness['matched_form']}', байт: {witness['byte_start']}, зона: '{zone}'). "
                        f"Пропозиція: '{proposed_ukr}' (оцінка: {score})"
                    )
                )
                self.db.insert_cycle(cycle)

                # 5. Keep work status as in_progress (do not mark analyzed after 1 term)
                with self.db.get_connection() as conn:
                    conn.execute(
                        "UPDATE works SET research_status = 'in_progress' WHERE id = ?",
                        (work_id,)
                    )
                    conn.commit()

                # 6. Refresh dictionary export
                try:
                    self.exporter.export_markdown()
                except Exception as ex:
                    logger.warning(f"Помилка оновлення словника: {ex}")

                res = {
                    "status": "committed",
                    "term": cand,
                    "matched_form": witness["matched_form"],
                    "proposed_ukr": proposed_ukr,
                    "score": score,
                    "work": work_title,
                    "author": author_name,
                    "zone": zone,
                    "byte_start": witness["byte_start"],
                    "eval_details": eval_res
                }
                if self.on_cycle_complete:
                    self.on_cycle_complete(res)
                return res

        return {
            "status": "idle",
            "message": f"Опрацьовано початкові фрагменти «{work_title}», нових валідних термінів не виявлено."
        }
