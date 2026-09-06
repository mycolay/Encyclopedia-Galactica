"""
Database Manager for AutoSciFi & Lexicon («Космослов»).
Uses SQLite with WAL mode, foreign keys, and FTS5 full-text search.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.models import Author, Work, SciFiTerm, ResearchCycle, NeologismInterpretation

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scifi_lexicon.db"


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            # Authors table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name_orig TEXT NOT NULL,
                name_ukr TEXT NOT NULL,
                birth_year INTEGER,
                death_year INTEGER,
                country TEXT NOT NULL,
                primary_language TEXT DEFAULT 'en',
                cult_tier INTEGER DEFAULT 1,
                cult_score REAL DEFAULT 0.0,
                awards_summary TEXT,
                trope_influence TEXT,
                bio_summary TEXT
            );
            """)

            # Works table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                author_id INTEGER NOT NULL,
                title_orig TEXT NOT NULL,
                title_ukr TEXT NOT NULL,
                year INTEGER NOT NULL,
                original_lang TEXT DEFAULT 'en',
                form TEXT DEFAULT 'Novel',
                subgenres_json TEXT DEFAULT '[]',
                awards_json TEXT DEFAULT '[]',
                canon_inclusions_json TEXT DEFAULT '[]',
                cult_score REAL DEFAULT 0.0,
                synopsis TEXT,
                has_full_text INTEGER DEFAULT 0,
                text_path TEXT,
                word_count INTEGER DEFAULT 0,
                research_status TEXT DEFAULT 'pending',
                FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
            );
            """)

            # Terms table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term_orig TEXT NOT NULL,
                ipa TEXT,
                work_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                original_context TEXT,
                context_source_locator TEXT,
                concept_category TEXT NOT NULL,
                scientific_definition TEXT NOT NULL,
                ukr_traditional TEXT,
                ukr_grinchenko_json TEXT DEFAULT '[]',
                morphological_rationale TEXT,
                ukr_translated_context TEXT,
                verification_score REAL DEFAULT 0.0,
                status TEXT DEFAULT 'verified',
                FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
            );
            """)

            # Research Cycles table (Karpathy AutoResearch loop)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS research_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                target_work_id INTEGER NOT NULL,
                target_work_title TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                llm_model TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                terms_discovered INTEGER DEFAULT 0,
                loss_or_quality_score REAL DEFAULT 0.0,
                status TEXT DEFAULT 'committed',
                notes TEXT,
                FOREIGN KEY (target_work_id) REFERENCES works(id) ON DELETE CASCADE
            );
            """)

            # Grinchenko Roots & Affixes
            conn.execute("""
            CREATE TABLE IF NOT EXISTS grinchenko_roots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_or_affix TEXT NOT NULL,
                type TEXT NOT NULL, -- prefix, root, suffix, pattern
                meaning TEXT NOT NULL,
                volume_page TEXT,
                productivity_notes TEXT
            );
            """)

            # Full-Text Search Virtual Tables
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS terms_fts USING fts5(
                term_orig,
                concept_category,
                scientific_definition,
                ukr_traditional,
                morphological_rationale,
                ukr_translated_context,
                content='terms',
                content_rowid='id'
            );
            """)

            conn.commit()

    # --- Author Operations ---
    def insert_author(self, author: Author) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("""
            INSERT INTO authors (slug, name_orig, name_ukr, birth_year, death_year, country,
                                primary_language, cult_tier, cult_score, awards_summary,
                                trope_influence, bio_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                cult_score=excluded.cult_score,
                cult_tier=excluded.cult_tier,
                awards_summary=excluded.awards_summary,
                trope_influence=excluded.trope_influence,
                bio_summary=excluded.bio_summary
            RETURNING id;
            """, (
                author.slug, author.name_orig, author.name_ukr, author.birth_year,
                author.death_year, author.country, author.primary_language,
                author.cult_tier, author.cult_score, author.awards_summary,
                author.trope_influence, author.bio_summary
            ))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_authors(self, limit: int = 100, order_by: str = "cult_score DESC") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(f"SELECT * FROM authors ORDER BY {order_by} LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_author_by_id(self, author_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM authors WHERE id = ?", (author_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- Work Operations ---
    def insert_work(self, work: Work) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("""
            INSERT INTO works (slug, author_id, title_orig, title_ukr, year, original_lang,
                              form, subgenres_json, awards_json, canon_inclusions_json,
                              cult_score, synopsis, has_full_text, text_path, word_count,
                              research_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                cult_score=excluded.cult_score,
                awards_json=excluded.awards_json,
                canon_inclusions_json=excluded.canon_inclusions_json,
                synopsis=excluded.synopsis,
                has_full_text=excluded.has_full_text,
                text_path=excluded.text_path,
                word_count=excluded.word_count,
                research_status=excluded.research_status
            RETURNING id;
            """, (
                work.slug, work.author_id, work.title_orig, work.title_ukr, work.year,
                work.original_lang, work.form, json.dumps(work.subgenres, ensure_ascii=False),
                json.dumps(work.awards, ensure_ascii=False),
                json.dumps(work.canon_inclusions, ensure_ascii=False),
                work.cult_score, work.synopsis, 1 if work.has_full_text else 0,
                work.text_path, work.word_count, work.research_status
            ))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_works(self, limit: int = 200, order_by: str = "cult_score DESC", author_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if author_id:
                cursor = conn.execute(
                    f"SELECT w.*, a.name_orig as author_name_orig, a.name_ukr as author_name_ukr "
                    f"FROM works w JOIN authors a ON w.author_id = a.id "
                    f"WHERE w.author_id = ? ORDER BY {order_by} LIMIT ?",
                    (author_id, limit)
                )
            else:
                cursor = conn.execute(
                    f"SELECT w.*, a.name_orig as author_name_orig, a.name_ukr as author_name_ukr "
                    f"FROM works w JOIN authors a ON w.author_id = a.id "
                    f"ORDER BY {order_by} LIMIT ?",
                    (limit,)
                )
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                d["subgenres"] = json.loads(d.get("subgenres_json") or "[]")
                d["awards"] = json.loads(d.get("awards_json") or "[]")
                d["canon_inclusions"] = json.loads(d.get("canon_inclusions_json") or "[]")
                results.append(d)
            return results

    def get_work_by_id(self, work_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT w.*, a.name_orig as author_name_orig, a.name_ukr as author_name_ukr "
                "FROM works w JOIN authors a ON w.author_id = a.id WHERE w.id = ?",
                (work_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["subgenres"] = json.loads(d.get("subgenres_json") or "[]")
            d["awards"] = json.loads(d.get("awards_json") or "[]")
            d["canon_inclusions"] = json.loads(d.get("canon_inclusions_json") or "[]")
            return d

    # --- Term Operations ---
    def insert_term(self, term: SciFiTerm) -> int:
        with self.get_connection() as conn:
            neologisms_json = json.dumps([n.dict() if hasattr(n, 'dict') else n for n in term.ukr_grinchenko_neologisms], ensure_ascii=False)
            cursor = conn.execute("""
            INSERT INTO terms (term_orig, ipa, work_id, author_id,
                              original_context, context_source_locator, concept_category,
                              scientific_definition, ukr_traditional, ukr_grinchenko_json,
                              morphological_rationale, ukr_translated_context,
                              verification_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """, (
                term.term_orig, term.ipa, term.work_id, term.author_id,
                term.original_context,
                term.context_source_locator, term.concept_category,
                term.scientific_definition, term.ukr_traditional,
                neologisms_json, term.morphological_rationale,
                term.ukr_translated_context, term.verification_score,
                term.status
            ))
            term_id = cursor.fetchone()[0]

            # Index in FTS5
            conn.execute("""
            INSERT INTO terms_fts (rowid, term_orig, concept_category, scientific_definition,
                                  ukr_traditional, morphological_rationale, ukr_translated_context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                term_id, term.term_orig, term.concept_category, term.scientific_definition,
                term.ukr_traditional or "", term.morphological_rationale or "", term.ukr_translated_context or ""
            ))

            conn.commit()
            return term_id

    def get_terms(self, limit: int = 100, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if search:
                cursor = conn.execute("""
                SELECT t.*, w.title_orig as work_title_orig, w.title_ukr as work_title_ukr,
                       a.name_orig as author_name_orig, a.name_ukr as author_name_ukr,
                       ea.earliest_year
                FROM terms t
                LEFT JOIN earliest_attestation ea ON t.term_orig = ea.term_orig
                JOIN terms_fts fts ON t.id = fts.rowid
                JOIN works w ON t.work_id = w.id
                JOIN authors a ON t.author_id = a.id
                WHERE terms_fts MATCH ?
                ORDER BY t.verification_score DESC
                LIMIT ?
                """, (search, limit))
            elif category:
                cursor = conn.execute("""
                SELECT t.*, w.title_orig as work_title_orig, w.title_ukr as work_title_ukr,
                       a.name_orig as author_name_orig, a.name_ukr as author_name_ukr,
                       ea.earliest_year
                FROM terms t
                LEFT JOIN earliest_attestation ea ON t.term_orig = ea.term_orig
                JOIN works w ON t.work_id = w.id
                JOIN authors a ON t.author_id = a.id
                WHERE t.concept_category = ?
                ORDER BY COALESCE(ea.earliest_year, 9999) ASC, t.id ASC
                LIMIT ?
                """, (category, limit))
            else:
                cursor = conn.execute("""
                SELECT t.*, w.title_orig as work_title_orig, w.title_ukr as work_title_ukr,
                       a.name_orig as author_name_orig, a.name_ukr as author_name_ukr,
                       ea.earliest_year
                FROM terms t
                LEFT JOIN earliest_attestation ea ON t.term_orig = ea.term_orig
                JOIN works w ON t.work_id = w.id
                JOIN authors a ON t.author_id = a.id
                ORDER BY COALESCE(ea.earliest_year, 9999) ASC, t.id ASC
                LIMIT ?
                """, (limit,))

            results = []
            for row in cursor.fetchall():
                d = dict(row)
                d["ukr_grinchenko_neologisms"] = json.loads(d.get("ukr_grinchenko_json") or "[]")
                results.append(d)
            return results

    def get_term_by_orig(self, term_orig: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM terms WHERE LOWER(term_orig) = LOWER(?)", (term_orig.strip(),))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["ukr_grinchenko_neologisms"] = json.loads(d.get("ukr_grinchenko_json") or "[]")
            return d

    def insert_attestation(self, attestation: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            keys = list(attestation.keys())
            placeholders = ", ".join("?" for _ in keys)
            cols = ", ".join(keys)
            cursor = conn.execute(
                f"INSERT INTO attestations ({cols}) VALUES ({placeholders}) RETURNING id;",
                [attestation[k] for k in keys]
            )
            att_id = cursor.fetchone()[0]
            conn.commit()
            return att_id

    # --- Research Cycle Operations ---
    def insert_cycle(self, cycle: ResearchCycle) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("""
            INSERT INTO research_cycles (timestamp, target_work_id, target_work_title,
                                        hypothesis, llm_model, prompt_tokens,
                                        completion_tokens, terms_discovered,
                                        loss_or_quality_score, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """, (
                cycle.timestamp.isoformat(), cycle.target_work_id, cycle.target_work_title,
                cycle.hypothesis, cycle.llm_model, cycle.prompt_tokens,
                cycle.completion_tokens, cycle.terms_discovered,
                cycle.loss_or_quality_score, cycle.status, cycle.notes
            ))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_cycles(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM research_cycles ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # --- System Stats ---
    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            authors_cnt = conn.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
            works_cnt = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
            texts_cnt = conn.execute("SELECT COUNT(*) FROM works WHERE has_full_text = 1").fetchone()[0]
            terms_cnt = conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0]
            cycles_cnt = conn.execute("SELECT COUNT(*) FROM research_cycles").fetchone()[0]
            return {
                "authors_count": authors_cnt,
                "works_count": works_cnt,
                "full_texts_count": texts_cnt,
                "terms_count": terms_cnt,
                "research_cycles_count": cycles_cnt
            }
