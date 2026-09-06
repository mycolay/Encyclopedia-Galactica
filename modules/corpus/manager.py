"""
Corpus Manager for AutoSciFi & Lexicon («Космослов»).
Manages original language text storage, chapter chunking, context extraction,
and public-domain fetching (Project Gutenberg / Standard Ebooks).
"""

import os
import re
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

DEFAULT_CORPUS_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "corpus" / "texts"


class CorpusManager:
    def __init__(self, corpus_root: Optional[str] = None):
        self.root = Path(corpus_root) if corpus_root else DEFAULT_CORPUS_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def get_work_path(self, author_slug: str, work_slug: str) -> Path:
        work_dir = self.root / author_slug / work_slug
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir / "original.txt"

    def store_text(self, author_slug: str, work_slug: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[Path, int]:
        """Stores original full text and its metadata."""
        file_path = self.get_work_path(author_slug, work_slug)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        word_count = len(text.split())

        meta_path = file_path.parent / "metadata.json"
        meta_data = metadata or {}
        meta_data["word_count"] = word_count
        meta_data["character_count"] = len(text)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        return file_path, word_count

    def load_text(self, author_slug: str, work_slug: str) -> Optional[str]:
        """Loads original full text if present."""
        file_path = self.get_work_path(author_slug, work_slug)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        return None

    def search_term_context(self, text: str, term: str, window_chars: int = 350) -> List[Dict[str, Any]]:
        """
        Locates occurrences of a term in text and extracts surrounding context sentences.
        """
        results = []
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start_pos = max(0, match.start() - window_chars)
            end_pos = min(len(text), match.end() + window_chars)

            # Adjust to sentence boundaries if possible
            snippet = text[start_pos:end_pos].strip()
            # Clean newlines for presentation
            clean_snippet = re.sub(r"\s+", " ", snippet)

            results.append({
                "exact_match": match.group(0),
                "position": match.start(),
                "context": clean_snippet
            })
            if len(results) >= 5:  # Limit top 5 occurrences
                break
        return results

    def fetch_gutenberg_text(self, gutenberg_id: int) -> Optional[str]:
        """Fetches public-domain text directly from Project Gutenberg mirrors."""
        urls = [
            f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
            f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"
        ]
        headers = {"User-Agent": "AutoSciFi-Lexicon-Scholar/1.0 (Educational Academic Research)"}
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    text = resp.text
                    # Strip standard Gutenberg header/footer
                    header_mark = "*** START OF THE PROJECT GUTENBERG"
                    footer_mark = "*** END OF THE PROJECT GUTENBERG"
                    if header_mark in text:
                        text = text.split(header_mark)[-1]
                        text = text.split("\n", 1)[-1]  # remove header title line
                    if footer_mark in text:
                        text = text.split(footer_mark)[0]
                    return text.strip()
            except Exception:
                continue
        return None
