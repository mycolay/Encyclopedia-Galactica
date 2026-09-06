"""
Local Ebook Importer for NAS Library.
Converts user-provided files (.txt, .md, .epub, .fb2) into the LLM-Ready format
on K:\\scifi_library with structured chapters and manifest.
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, List
from modules.corpus.manager import CorpusManager
from core.db import DatabaseManager


class EbookImporter:
    def __init__(self, corpus_mgr: CorpusManager, db: DatabaseManager):
        self.corpus_mgr = corpus_mgr
        self.db = db

    def extract_text_from_epub(self, epub_path: Path) -> str:
        """Extracts clean ordered text from an EPUB container without third-party dependencies."""
        text_parts = []
        with zipfile.ZipFile(str(epub_path), "r") as z:
            # Find all HTML/XHTML documents
            html_files = [f for f in z.namelist() if f.lower().endswith((".xhtml", ".html", ".htm"))]
            # Exclude cover and nav files if possible
            content_files = [f for f in html_files if not any(x in f.lower() for x in ["cover", "nav", "toc"])]
            target_files = content_files if content_files else html_files

            for fname in target_files:
                raw_bytes = z.read(fname)
                try:
                    html_content = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    html_content = raw_bytes.decode("latin-1", errors="ignore")

                # Remove script and style elements
                clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
                # Convert header tags to markdown
                clean = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n\n# \1\n\n", clean, flags=re.IGNORECASE)
                clean = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n\n## \1\n\n", clean, flags=re.IGNORECASE)
                clean = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n\n### \1\n\n", clean, flags=re.IGNORECASE)
                clean = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", clean, flags=re.IGNORECASE)
                clean = re.sub(r"<br\s*/?>", r"\n", clean, flags=re.IGNORECASE)
                # Strip remaining HTML tags
                clean = re.sub(r"<[^>]+>", "", clean)
                # Unescape HTML entities
                import html
                clean = html.unescape(clean)
                clean = re.sub(r"\n{3,}", "\n\n", clean).strip()

                if len(clean) > 80:
                    text_parts.append(clean)

        return "\n\n".join(text_parts)

    def extract_text_from_file(self, file_path: Path) -> str:
        """Extracts text based on file format."""
        suffix = file_path.suffix.lower()
        if suffix in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif suffix == ".epub":
            return self.extract_text_from_epub(file_path)
        elif suffix == ".fb2":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Basic FB2 tag stripping
                clean = re.sub(r"<[^>]+>", " ", content)
                return re.sub(r"\s+", " ", clean).strip()
        else:
            raise ValueError(f"Непідтримуваний формат файлу: {suffix}")

    def import_book(
        self,
        file_path: str,
        title_orig: str,
        author_name: str,
        year: int,
        title_ukr: Optional[str] = None,
        author_ukr: Optional[str] = None,
        original_lang: str = "en",
        subgenres: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Imports an ebook into NAS K:\\scifi_library."""
        fpath = Path(file_path)
        if not fpath.exists():
            raise FileNotFoundError(f"Файл не знайдено: {file_path}")

        raw_text = self.extract_text_from_file(fpath)

        def slugify(text: str) -> str:
            return re.sub(r"[^\w]+", "-", text.lower()).strip("-")

        author_slug = slugify(author_name)
        work_slug = slugify(title_orig)

        # 1. Package to NAS
        pkg_res = self.corpus_mgr.package_llm_ready_work(
            author_slug=author_slug,
            work_slug=work_slug,
            text=raw_text,
            metadata={
                "title": title_orig,
                "title_ukr": title_ukr or title_orig,
                "author_name": author_name,
                "author_ukr": author_ukr or author_name,
                "year": year,
                "original_lang": original_lang,
                "subgenres": subgenres or ["Science Fiction"]
            }
        )

        # 2. Update Database
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM authors WHERE slug = ?", (author_slug,))
            row = cursor.fetchone()
            if not row:
                cursor = conn.execute("""
                INSERT INTO authors (slug, name_orig, name_ukr, country, primary_language, cult_tier, cult_score)
                VALUES (?, ?, ?, 'Global', ?, 2, 85.0) RETURNING id;
                """, (author_slug, author_name, author_ukr or author_name, original_lang))
                author_id = cursor.fetchone()[0]
            else:
                author_id = row[0]

            conn.execute("""
            INSERT INTO works (slug, author_id, title_orig, title_ukr, year, original_lang,
                              form, subgenres_json, awards_json, cult_score, synopsis,
                              has_full_text, text_path, word_count, research_status)
            VALUES (?, ?, ?, ?, ?, ?, 'Novel', '[]', '[]', 85.0, ?, 1, ?, ?, 'pending')
            ON CONFLICT(slug) DO UPDATE SET
                has_full_text = 1,
                text_path = excluded.text_path,
                word_count = excluded.word_count;
            """, (
                work_slug, author_id, title_orig, title_ukr or title_orig,
                year, original_lang, f"Імпортовано з {fpath.name}",
                pkg_res["full_text_path"], pkg_res["word_count"]
            ))
            conn.commit()

        return pkg_res
