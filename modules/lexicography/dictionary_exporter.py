"""
Academic Dictionary Exporter for Sci-Fi Neologisms.
Generates comprehensive Markdown documents and JSON-LD for academic dissemination.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.db import DatabaseManager

DEFAULT_OUTPUT_MD = Path(__file__).resolve().parent.parent.parent / "docs" / "SCI_FI_LEXICON.md"


class DictionaryExporter:
    def __init__(self, db: DatabaseManager, output_path: Optional[Path] = None):
        self.db = db
        self.output_path = output_path or DEFAULT_OUTPUT_MD
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def export_markdown(self) -> Path:
        """Exports the entire database of Sci-Fi terms into an academic Markdown dictionary."""
        terms = self.db.get_terms(limit=1000)
        stats = self.db.get_stats()

        lines = [
            "# СЛОВНИК НАУКОВО-ФАНТАСТИЧНИХ НЕОЛОГІЗМІВ ТА КОНЦЕПТІВ («КОСМОСЛОВ»)",
            "## Академічний звід авторських термінів світової НФ з творчою українською інтерпретацією на основі моделей Словника Бориса Грінченка",
            "",
            "> **Статус проєкту**: Фундаментальне дослідження корпусу культової наукової фантастики.",
            f"> **Кількість опрацьованих термінів**: {stats['terms_count']} | **Творів у каталозі**: {stats['works_count']} | **Авторів**: {stats['authors_count']}",
            "",
            "---",
            "",
            "## Вступні зауваги та науковий метод",
            "Наукова фантастика є унікальним генератором понять, яких не існувало в реальності на момент їх написання.",
            "Переклад таких понять нерідко зводився або до механічної транслітерації (калькування англійського звучання),",
            "або до штучних росіянізмів. Наш метод спирається на внутрішні словотвірні закони української мови,",
            "зафіксовані у чотиритомному «Словарі української мови» за ред. Бориса Грінченка (1907–1909),",
            "що дозволяє відродити живу, природну образність термінів без спотворення їхньої фізичної чи філософської суті.",
            "",
            "---",
            ""
        ]

        # Group by category
        categories = {}
        for t in terms:
            cat = t.get("concept_category", "Загальні концепти")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(t)

        for cat_name, cat_terms in categories.items():
            lines.append(f"## Розділ: {cat_name.upper()}")
            lines.append("")

            for term in cat_terms:
                term_orig = term["term_orig"].upper()
                ipa = term.get("ipa", "")
                author_orig = term.get("author_name_orig", "")
                author_ukr = term.get("author_name_ukr", "")
                work_orig = term.get("work_title_orig", "")
                work_ukr = term.get("work_title_ukr", "")
                year = term.get("first_attestation_year", "")
                def_sci = term.get("scientific_definition", "")
                orig_context = term.get("original_context", "")
                locator = term.get("context_source_locator", "")
                trad = term.get("ukr_traditional", "")
                rationale = term.get("morphological_rationale", "")
                trans_ctx = term.get("ukr_translated_context", "")
                neologisms = term.get("ukr_grinchenko_neologisms", [])

                lines.append(f"### ❖ {term_orig} {f'`{ipa}`' if ipa else ''}")
                lines.append(f"- **Першотвір та авторство**: **{author_ukr}** ({author_orig}), *«{work_ukr}»* (*{work_orig}*), **{year} рік**.")
                if locator:
                    lines.append(f"- **Локація у тексті**: {locator}")
                lines.append(f"- **Науково-концептуальне визначення**: {def_sci}")
                lines.append("")
                lines.append(f"> **Контекст першої появи (мовою оригіналу)**:")
                lines.append(f"> «{orig_context}»")
                lines.append("")
                lines.append(f"- **Традиційний переклад у виданнях**: *{trad}*")
                lines.append("")
                lines.append("**Творча українська інтерпретація за моделями словника Грінченка**:")
                for n in neologisms:
                    variant = n.get("variant", "")
                    morphemes = n.get("morphemes", "")
                    model = n.get("grinchenko_model", "")
                    nuance = n.get("semantic_nuance", "")
                    lines.append(f"  * **{variant}**")
                    lines.append(f"    - *Морфемна будова*: {morphemes}")
                    lines.append(f"    - *Зразок за Грінченком*: {model}")
                    lines.append(f"    - *Семантичний відтінок*: {nuance}")
                lines.append("")
                lines.append(f"- **Академічне обґрунтування словотвору**: {rationale}")
                lines.append("")
                lines.append(f"> **Приклад художнього втілення в українському контексті**:")
                lines.append(f"> «{trans_ctx}»")
                lines.append("")
                lines.append("---")
                lines.append("")

        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return self.output_path
