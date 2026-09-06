"""
Побудова перевірної основи зі словника Грінченка.

Що цей скрипт дає і чого НЕ дає — прямо, без прикрас.

ДАЄ:
  * байт-адресовний артефакт `hrinchenko.txt` з відомим sha256;
  * покажчик усіх реєстрових слів із координатою (байт, довжина);
  * номер тому за абеткою, підтверджений позицією в артефакті;
  * відповідь «чи існує це слово у Грінченка взагалі» — головне питання.

НЕ ДАЄ:
  * номерів сторінок ДРУКОВАНИХ томів. Це PDF-передрук зі своєю суцільною
    пагінацією 1-2971; оригінальної пагінації в тексті немає. Отже
    твердження «т. IV, с. 293» перевіряється лише частково: том — так,
    сторінка — ні. Це записується як обмеження, а не замовчується.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypdf import PdfReader

SCRATCH = Path(
    "C:/Users/mmk/AppData/Local/Temp/claude/"
    "C--ai-server-the--best-book/6387c107-ad62-4446-ad89-4439dc935ed5/scratchpad"
)
PDF = SCRATCH / "hrinchenko_1907_1909.pdf"
OUT_DIR = Path("K:/scifi_library/lexicons/hrinchenko-1907-1909")
OUT_TXT = OUT_DIR / "hrinchenko.txt"

RUNNING_HEAD = re.compile(r"^«Словарь української мови» Бориса Грінченка\s*\d*\s*$")

# Реєстрове слово: з початку рядка, кирилиця (з дореформеними ѣ, ъ, і),
# далі кома й граматична позначка. Наголоси всередині слова допустимі.
# Стаття буває трьох форм:
#   "Америка, -ки, ж. ..."                 - слово + граматика
#   "Бездоріжжя, бездорожжя, -жя, с. ..."  - слово + варіант через кому
#   "Аминь и амінь, нар. ..."              - слово + варіант через "и"
# Перший шаблон допускав лише першу форму і мовчки губив статті з
# варіантами - через що звірка дала ХИБНЕ спростування для "бездоріжжя".
_WORD = r"[а-яїієґёъьѣ́’'\-]{1,40}"
HEADWORD_RE = re.compile(
    r"^([А-ЯЇІЄҐЂѢ]" + _WORD + r")"
    r"(?:(?:\s*,\s*|\s+и\s+)" + _WORD + r"){0,3}"
    r"\s*,\s*(?:-|[а-яїієґ]{1,6}\.|=)",
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def extract() -> tuple[bytes, list[tuple[int, int]]]:
    """Повертає (текст артефакту, [(байт_початку_сторінки, номер_сторінки)])."""
    reader = PdfReader(str(PDF))
    chunks: list[bytes] = []
    page_offsets: list[tuple[int, int]] = []
    pos = 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        lines = [ln for ln in text.split("\n") if not RUNNING_HEAD.match(ln.strip())]
        body = ("\n".join(lines).strip() + "\n").encode("utf-8")
        page_offsets.append((pos, i))
        chunks.append(body)
        pos += len(body)
        if i % 400 == 0:
            print(f"  сторінок оброблено: {i}", flush=True)
    return b"".join(chunks), page_offsets


def index_headwords(data: bytes) -> list[dict]:
    """Знаходить реєстрові слова з байтовими координатами."""
    text = data.decode("utf-8", errors="replace")
    entries: list[dict] = []
    # Байтова позиція рахується ІНКРЕМЕНТНО. Раніше тут стояло
    # len(text[:char_pos].encode()) для кожного з 61 тис. збігів — O(n^2)
    # на 13.8 МБ тексту, тобто години замість секунд.
    byte_pos = 0
    for line in text.splitlines():
        line_bytes = len(line.encode("utf-8"))
        m = HEADWORD_RE.match(line)
        if m:
            hw = m.group(1).strip()
            entries.append(
                {
                    "headword": hw,
                    "normalized": hw.replace("́", "").lower(),
                    "byte_start": byte_pos,
                    "byte_len": line_bytes,
                }
            )
        byte_pos += line_bytes + 1  # +1 за перевід рядка
    return entries


def main() -> int:
    if not PDF.exists():
        print(f"PDF не знайдено: {PDF}")
        return 1

    print(f"витягування тексту з {PDF.name} ...", flush=True)
    data, page_offsets = extract()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_bytes(data)

    digest = sha256_bytes(data)
    print(f"\nартефакт: {OUT_TXT}")
    print(f"  байтів      : {len(data):,}")
    print(f"  sha256      : {digest}")
    print(f"  сторінок    : {len(page_offsets)}")

    entries = index_headwords(data)
    print(f"\nреєстрових слів знайдено: {len(entries):,}")
    print("  перші 8:", ", ".join(e["headword"] for e in entries[:8]))
    print("  останні 5:", ", ".join(e["headword"] for e in entries[-5:]))

    # контроль: координати мусять вказувати саме на своє слово
    bad = 0
    for e in entries[::997]:
        at = data[e["byte_start"]: e["byte_start"] + e["byte_len"]]
        if not at.decode("utf-8", errors="replace").startswith(e["headword"][:6]):
            bad += 1
    print(f"  контроль координат (кожне 997-ме): розбіжностей {bad}")

    import json
    (OUT_DIR / "headwords.json").write_text(
        json.dumps(
            {"artifact_sha256": digest, "count": len(entries), "entries": entries},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nпокажчик: {OUT_DIR / 'headwords.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
