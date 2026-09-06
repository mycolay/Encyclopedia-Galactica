"""
Library Catalog Report Generator (Т7 - COSMOSLOV_TZ_EXECUTOR_V2)
Generates docs/LIBRARY_CATALOG.md aggregating works, acquisition receipts, words, characters, and provenance.
"""

import os
import sys
from pathlib import Path
import sqlite3
from typing import Dict, Any, List

def generate_catalog_report(
    db_path: str = "data/scifi_lexicon.db",
    output_path: str = "docs/LIBRARY_CATALOG.md"
) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 1. Gather all works joined with their latest acquisition receipt
    sql = """
    SELECT 
        w.id,
        w.slug,
        w.title_orig,
        w.title_ukr,
        a.name_orig AS author_name,
        w.year,
        w.original_lang,
        w.has_full_text,
        w.text_path,
        w.word_count,
        w.research_status,
        r.edition_id,
        r.is_translation,
        r.acquisition_class,
        r.rights,
        r.rights_basis,
        r.clean_bytes,
        r.clean_sha256
    FROM works w
    LEFT JOIN authors a ON w.author_id = a.id
    LEFT JOIN acquisition_receipts r ON w.slug = r.work_slug
    ORDER BY w.year ASC, w.title_orig ASC
    """
    rows = conn.execute(sql).fetchall()

    # Deduplicate by work slug (picking the primary receipt)
    works_map = {}
    for r in rows:
        slug = r["slug"]
        if slug not in works_map:
            works_map[slug] = r
        else:
            # If multiple receipts, prefer verified over synthetic/absent
            if r["acquisition_class"] == "verified" and works_map[slug]["acquisition_class"] != "verified":
                works_map[slug] = r

    # Count statistics strictly matching database SELECTs
    total_works = conn.execute("SELECT count(*) FROM works").fetchone()[0]
    verified_works = conn.execute("SELECT count(*) FROM works WHERE has_full_text = 1").fetchone()[0]
    in_copyright_receipts = conn.execute("SELECT count(*) FROM acquisition_receipts WHERE rights = 'in_copyright'").fetchone()[0]
    quarantined_receipts = conn.execute("SELECT count(*) FROM acquisition_receipts WHERE acquisition_class = 'synthetic'").fetchone()[0]
    not_found_receipts = conn.execute("SELECT count(*) FROM acquisition_receipts WHERE acquisition_class = 'absent' AND rights != 'in_copyright'").fetchone()[0]

    # Total characters / bytes in verified corpus
    total_bytes = 0
    total_words = 0
    for w in works_map.values():
        if w["has_full_text"] == 1 and w["text_path"] and os.path.exists(w["text_path"]):
            try:
                b = open(w["text_path"], "rb").read()
                total_bytes += len(b)
                total_words += w["word_count"] or len(b.decode("utf-8", errors="ignore").split())
            except Exception:
                pass

    # Build markdown table
    md_lines = [
        "# Каталог Бібліотеки Космослов (Library Catalog)",
        "",
        "> Автоматично згенеровано модулем `modules/corpus/catalog_report.py` на основі `acquisition_receipts` та БД.",
        "",
        "## 1. Реєстр творів та чеків набуття",
        "",
        "| Твір | Рік | Мова | Автор | Оригінал/переклад | Клас | Слів | Джерело | Права |",
        "| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- |"
    ]

    for slug, w in sorted(works_map.items(), key=lambda x: (x[1]["year"] or 0, x[1]["title_orig"])):
        title = w["title_orig"]
        year = w["year"] or "—"
        lang = w["original_lang"] or "en"
        author = w["author_name"] or "—"
        is_trans = "Переклад" if w["is_translation"] == 1 else "Оригінал"
        acq_class = w["acquisition_class"] or ("verified" if w["has_full_text"] == 1 else "absent")
        words = f"{w['word_count']:,}" if w["word_count"] else "—"
        edition = w["edition_id"] or "—"
        rights = w["rights"] or "unknown"

        md_lines.append(
            f"| **{title}** | {year} | `{lang}` | {author} | {is_trans} | `{acq_class}` | {words} | `{edition}` | `{rights}` |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## 2. Підсумок стану бібліотеки",
        "",
        "```",
        f"Усього творів у каталозі:        {total_works}",
        f"З перевіреним повним текстом:    {verified_works}",
        f"Відсутні через копірайт:         {in_copyright_receipts}",
        f"У карантині (синтетика):         {quarantined_receipts}",
        f"Не знайдено:                     {not_found_receipts}",
        f"Загальний обсяг корпусу:         {total_bytes:,} символів (байтів LF)",
        f"Загальна кількість слів:         {total_words:,} слів",
        "```",
        ""
    ])

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "wb") as f:
        f.write("\n".join(md_lines).encode("utf-8"))

    conn.close()

    summary = {
        "total_works": total_works,
        "verified_works": verified_works,
        "in_copyright_works": in_copyright_receipts,
        "quarantined_works": quarantined_receipts,
        "not_found_works": not_found_receipts,
        "total_bytes": total_bytes,
        "total_words": total_words
    }
    return summary

if __name__ == "__main__":
    s = generate_catalog_report()
    print("Catalog report generated in docs/LIBRARY_CATALOG.md:")
    for k, v in s.items():
        print(f"  {k}: {v}")
