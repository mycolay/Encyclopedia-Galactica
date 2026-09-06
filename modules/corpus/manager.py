"""
Corpus Manager for AutoSciFi & Lexicon («Космослов»).
Manages NAS library storage (K:\\scifi_library) and LLM-Ready text packaging:
- Unabridged full_text.md with clean YAML Frontmatter
- Structured chapter-by-chapter segmentation (chapters/chapter_XX.md)
- Semantic manifest.json for LLM context window planning
- Fast context search and fallback support
"""

import os
import re
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# NAS default path, with local directory as fallback
NAS_CORPUS_ROOT = Path(r"K:\scifi_library")
LOCAL_CORPUS_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "corpus" / "texts"


class CorpusManager:
    def __init__(self, corpus_root: Optional[str] = None):
        if corpus_root:
            self.root = Path(corpus_root)
        elif NAS_CORPUS_ROOT.parent.exists():
            self.root = NAS_CORPUS_ROOT
        else:
            self.root = LOCAL_CORPUS_ROOT

        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self.is_nas_active = ("K:" in str(self.root).upper())
        except Exception:
            self.root = LOCAL_CORPUS_ROOT
            self.root.mkdir(parents=True, exist_ok=True)
            self.is_nas_active = False

    def get_work_dir(self, author_slug: str, work_slug: str) -> Path:
        work_dir = self.root / "authors" / author_slug / work_slug
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    def get_work_path(self, author_slug: str, work_slug: str) -> Path:
        """Backward-compatible path to primary text file."""
        work_dir = self.get_work_dir(author_slug, work_slug)
        # Check if full_text.md or original.txt exists
        if (work_dir / "full_text.md").exists():
            return work_dir / "full_text.md"
        return work_dir / "original.txt"

    def split_into_chapters(self, text: str) -> List[Dict[str, Any]]:
        """
        Intelligently splits full text into chapters or logical segments.
        Supports standard English, Czech, Polish, and Ukrainian chapter delimiters.
        """
        chapter_pattern = re.compile(
            r"(?im)^(?:\s*)"
            r"(?:#+\s*)?"
            r"(?:chapter|act|book|part|canto|глава|розділ|действие|часть|scene)\b[^\n\r]*$",
            re.MULTILINE
        )

        matches = list(chapter_pattern.finditer(text))
        chapters = []

        if len(matches) >= 2:
            # We have identified structured chapters!
            # Preamble / Prologue before first match if significant
            if matches[0].start() > 200:
                preamble_text = text[:matches[0].start()].strip()
                if len(preamble_text.split()) > 40:
                    chapters.append({
                        "index": 0,
                        "title": "Prologue / Introduction",
                        "content": preamble_text,
                        "word_count": len(preamble_text.split())
                    })

            for i, match in enumerate(matches):
                start_idx = match.start()
                end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                ch_content = text[start_idx:end_idx].strip()
                ch_title = match.group(0).strip().lstrip("#").strip()

                chapters.append({
                    "index": len(chapters) + 1,
                    "title": ch_title,
                    "content": ch_content,
                    "word_count": len(ch_content.split())
                })
        else:
            # Fallback for texts without explicit chapter labels:
            # Segment into natural LLM-friendly chunks of ~3000 words each
            words = text.split()
            chunk_size = 3000
            for idx in range(0, len(words), chunk_size):
                ch_slice = words[idx:idx + chunk_size]
                ch_content = " ".join(ch_slice)
                ch_num = (idx // chunk_size) + 1
                chapters.append({
                    "index": ch_num,
                    "title": f"Section {ch_num}",
                    "content": ch_content,
                    "word_count": len(ch_slice)
                })

        return chapters

    def package_llm_ready_work(
        self,
        author_slug: str,
        work_slug: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates an LLM-Ready package on NAS:
        1. full_text.md with clean YAML Frontmatter
        2. chapters/chapter_XX.md for isolated chunk evaluation
        3. manifest.json for high-level agent navigation
        4. original.txt for raw legacy compatibility
        """
        work_dir = self.get_work_dir(author_slug, work_slug)
        meta = metadata or {}

        # 1. Clean raw text (remove excessive whitespace, normalize newlines)
        clean_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        word_count = len(clean_text.split())
        token_estimate = int(word_count * 1.35)

        # 2. Extract chapters
        chapters = self.split_into_chapters(clean_text)

        # 3. Create chapters directory
        chapters_dir = work_dir / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)

        chapter_manifest_items = []
        for ch in chapters:
            ch_num_str = f"{ch['index']:02d}"
            ch_filename = f"chapter_{ch_num_str}.md"
            ch_path = chapters_dir / ch_filename

            ch_header = (
                f"# {ch['title']}\n"
                f"> **Автор**: {meta.get('author_name', author_slug)} | **Твір**: {meta.get('title', work_slug)}\n"
                f"> **Обсяг**: {ch['word_count']} слів (~{int(ch['word_count'] * 1.35)} токенів)\n\n"
            )
            ch_data = (ch_header + ch["content"]).replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
            with open(ch_path, "wb") as f:
                f.write(ch_data)

            chapter_manifest_items.append({
                "index": ch["index"],
                "title": ch["title"],
                "filename": ch_filename,
                "relative_path": f"chapters/{ch_filename}",
                "word_count": ch["word_count"],
                "token_estimate": int(ch["word_count"] * 1.35)
            })

        # 4. Generate full_text.md with YAML frontmatter
        frontmatter = (
            "---\n"
            f"title: \"{meta.get('title', work_slug)}\"\n"
            f"title_ukr: \"{meta.get('title_ukr', '')}\"\n"
            f"author: \"{meta.get('author_name', author_slug)}\"\n"
            f"author_slug: \"{author_slug}\"\n"
            f"work_slug: \"{work_slug}\"\n"
            f"year: {meta.get('year', 0)}\n"
            f"language: \"{meta.get('original_lang', 'en')}\"\n"
            f"word_count: {word_count}\n"
            f"estimated_tokens: {token_estimate}\n"
            f"chapters_count: {len(chapters)}\n"
            f"format: \"LLM-Ready Markdown\"\n"
            f"storage: \"NAS ({self.root})\"\n"
            "---\n\n"
        )

        full_text_path = work_dir / "full_text.md"
        full_text_bytes = (frontmatter + clean_text).replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        with open(full_text_path, "wb") as f:
            f.write(full_text_bytes)

        # 5. Legacy original.txt for backwards compatibility
        original_txt_path = work_dir / "original.txt"
        clean_bytes = clean_text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        with open(original_txt_path, "wb") as f:
            f.write(clean_bytes)

        # 6. Generate manifest.json
        manifest_data = {
            "work_slug": work_slug,
            "author_slug": author_slug,
            "title": meta.get("title", work_slug),
            "title_ukr": meta.get("title_ukr", ""),
            "author_name": meta.get("author_name", author_slug),
            "year": meta.get("year", 0),
            "original_lang": meta.get("original_lang", "en"),
            "word_count": word_count,
            "estimated_tokens": token_estimate,
            "chapters_count": len(chapters),
            "files": {
                "full_text": "full_text.md",
                "original_raw": "original.txt",
                "manifest": "manifest.json",
                "chapters_dir": "chapters/"
            },
            "chapters": chapter_manifest_items
        }

        manifest_path = work_dir / "manifest.json"
        manifest_bytes = json.dumps(manifest_data, ensure_ascii=False, indent=2).replace("\r\n", "\n").encode("utf-8")
        with open(manifest_path, "wb") as f:
            f.write(manifest_bytes)

        return {
            "work_dir": str(work_dir),
            "full_text_path": str(full_text_path),
            "manifest_path": str(manifest_path),
            "chapters_count": len(chapters),
            "word_count": word_count,
            "is_nas": self.is_nas_active
        }

    def store_text(self, author_slug: str, work_slug: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[Path, int]:
        """Backward-compatible store_text wrapper delegating to package_llm_ready_work."""
        res = self.package_llm_ready_work(author_slug, work_slug, text, metadata)
        return Path(res["full_text_path"]), res["word_count"]

    def load_text(self, author_slug: str, work_slug: str) -> Optional[str]:
        """Loads clean full text if present."""
        path = self.get_work_path(author_slug, work_slug)
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Strip frontmatter if reading raw text
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        return parts[2].strip()
                return content
        return None

    def load_chapter(self, author_slug: str, work_slug: str, chapter_index: int) -> Optional[str]:
        """Loads a specific chapter for isolated LLM context analysis."""
        ch_filename = f"chapter_{chapter_index:02d}.md"
        ch_path = self.get_work_dir(author_slug, work_slug) / "chapters" / ch_filename
        if ch_path.exists():
            with open(ch_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        return None

    def load_manifest(self, author_slug: str, work_slug: str) -> Optional[Dict[str, Any]]:
        manifest_path = self.get_work_dir(author_slug, work_slug) / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def search_term_context(self, text: str, term: str, window_chars: int = 350) -> List[Dict[str, Any]]:
        results = []
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start_pos = max(0, match.start() - window_chars)
            end_pos = min(len(text), match.end() + window_chars)

            snippet = text[start_pos:end_pos].strip()
            clean_snippet = re.sub(r"\s+", " ", snippet)

            results.append({
                "exact_match": match.group(0),
                "position": match.start(),
                "context": clean_snippet
            })
            if len(results) >= 5:
                break
        return results

    def get_storage_stats(self) -> Dict[str, Any]:
        """Returns disk and library usage statistics."""
        import shutil
        total, used, free = shutil.disk_usage(str(self.root))
        authors_dir = self.root / "authors"
        works_count = 0
        authors_count = 0
        total_words = 0

        if authors_dir.exists():
            for a_dir in authors_dir.iterdir():
                if a_dir.is_dir():
                    authors_count += 1
                    for w_dir in a_dir.iterdir():
                        if w_dir.is_dir() and (w_dir / "manifest.json").exists():
                            works_count += 1
                            try:
                                with open(w_dir / "manifest.json", "r", encoding="utf-8") as f:
                                    m = json.load(f)
                                    total_words += m.get("word_count", 0)
                            except Exception:
                                pass

        return {
            "root_path": str(self.root),
            "is_nas": self.is_nas_active,
            "disk_total_gb": round(total / (1024 ** 3), 2),
            "disk_used_gb": round(used / (1024 ** 3), 2),
            "disk_free_gb": round(free / (1024 ** 3), 2),
            "authors_count": authors_count,
            "works_count": works_count,
            "total_words_stored": total_words
        }
