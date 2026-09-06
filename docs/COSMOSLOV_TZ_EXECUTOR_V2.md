# ТЗ для виконавця — Космослов, редакція 2

Замінює `COSMOSLOV_TZ_EXECUTOR.md`. Увібрано `COSMOSLOV_TZ_ADDENDUM.md`
(доповнення Д0–Д8), три з них — у виправленому вигляді, підстави в §Розбір.

Ти виконавець. Робиш задачі ПО ЧЕРЗІ. Після кожної — запускаєш її тест.
Тест червоний → зупиняєшся, далі не йдеш.

Робоча тека: `C:\ai_server\the _best_book`
База: `data\scifi_lexicon.db`
Бібліотека: `K:\scifi_library\authors\<автор>\<твір>\`

---

## Т0. КОДУВАННЯ КОНСОЛІ — ЗРОБИ ПЕРШИМ

Консоль тут cp1252 і **падає на українських літерах**. Побачиш
`UnicodeEncodeError: 'charmap' codec can't encode` — це кодування консолі,
**а не помилка твого коду**. Не «лагодь» код, не переписуй тести латиницею.

**PowerShell** (основна оболонка тут):
```powershell
$env:PYTHONIOENCODING = "utf-8"
```

**Bash / Git Bash:**
```bash
export PYTHONIOENCODING=utf-8
```

Перевірка:
```powershell
$env:PYTHONIOENCODING="utf-8"; python -c "print('українські літери — ок')"
```

У тестах нижче команди наведено у формі bash. У PowerShell `&&` **не працює** —
заміняй на `;` або пиши команди окремими рядками.

---

## Т0.1. ЗАХИСТ БАЙТІВ ВІД CRLF — ЗРОБИ ДРУГИМ

**Це найнебезпечніша пастка проєкту.** Windows пише `\r\n`, Gutenberg
віддає `\n`. Якщо Git або текстовий редактор змінить переводи рядків:

1. `artifact_sha256` зміниться → всі свідки стануть `artifact_drift`;
2. кожен `byte_start` попливе на +1 байт за кожен попередній рядок;
3. вся доказова база стане недійсною **тихо**, без жодної помилки.

### Дії

**1. Читання і запис корпусу — ТІЛЬКИ бінарні.** Ніде в коді корпусу не
має бути `open(path)` чи `open(path,'r')`. Тільки `'rb'` / `'wb'`.

**2. Нормалізація до LF у `clean_gutenberg_text`** — до обрахунку
`clean_sha256` і до запису на диск:
```python
data = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
```

**3. `.gitattributes` у корені репозиторію.**

УВАГА — тут виправлення проти доповнення Д1. У ньому було
`*.md text eol=lf`, але **11 із 17** шляхів корпусу — це `.md`
(`full_text.md`, `chapters/*.md`). Правило за розширенням дозволило б Git
нормалізувати саме ті файли, у які дивляться координати свідків.
Тому правила — **за шляхом, не за розширенням**:

```gitattributes
# типово: текстові файли з LF
* text=auto eol=lf

# КОРПУС — недоторканні байти, незалежно від розширення
data/corpus/**        -text -diff
K:/scifi_library/**   -text -diff
*.QUARANTINE.txt      -text -diff

# документація — звичайний текст
docs/*.md   text eol=lf
*.py        text eol=lf
```

**Тест приймання Т0.1:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3,os
c=sqlite3.connect('data/scifi_lexicon.db')
bad=[]
for (p,) in c.execute('select text_path from works where has_full_text=1'):
    if p and os.path.exists(p):
        if b'\r\n' in open(p,'rb').read(): bad.append(os.path.basename(p))
print('файлів із CRLF:',len(bad),bad[:5])
"
```
Очікується `файлів із CRLF: 0`.

---

## ГОЛОВНЕ ПРАВИЛО

**Ти ніколи не пишеш текст художнього твору сам. Ніколи не пишеш цитату сам.
Ніколи не пишеш номер тому чи сторінки словника сам.**

Бракує тексту — не додумуєш. Пишеш `NOT_FOUND` і йдеш далі.

Причина: у проєкті вже сталася аварія. Хтось згенерував «оригінальні тексти»
замість завантажити. У чеському `člověka` виявили кирилічні `к` і `а` — так
пише мовна модель, так не пише жоден скан. 6 файлів і 5 статей недійсні.
Твоє завдання — прибрати наслідки, а не додати нових.

### 7 заборон (порушення = зупинка)

1. Не вигадувати текст твору. Не «відновлювати по пам'яті». Не переказувати.
2. Не вигадувати цитат. Цитата — ТІЛЬКИ читанням файлу з диска.
3. Не вигадувати посилань на Грінченка (том, сторінка).
4. Не заповнювати порожнє поле «правдоподібним». Порожнє = `NULL`.
5. Не видаляти й не редагувати файли текстів. Тільки позначати.
6. Не змінювати поріг чи критерій після того, як побачив результат.
7. Не писати «перша поява». Писати «найраніша знайдена в нашому корпусі».

---

## ЩО ВЖЕ Є

Робоче — використовуй:

| Файл | Що дає |
| --- | --- |
| `modules/corpus/harvester.py` | `fetch_from_gutenberg(id)`, `clean_gutenberg_text(txt)` |
| `modules/corpus/manager.py` | `search_term_context`, `package_llm_ready_work` |
| `core/db.py` | `DatabaseManager.get_connection()` |

Зламане — буде замінено, поки не чіпай:

| Файл | Проблема |
| --- | --- |
| `modules/autoresearch/evaluator.py` | пропускає вигадані цитати з оцінкою 0.91 |
| `modules/autoresearch/loop.py` | читає перші 1800 символів = 0.7% корпусу |
| `modules/lexicography/grinchenko_engine.py` | приймає `12345`, відхиляє `мислитель` |

## СТАН КОРПУСУ

**10 справжніх** (Gutenberg, 30–100 тис. слів): Frankenstein, Journey to the
Centre of the Earth, From the Earth to the Moon, Twenty Thousand Leagues,
Flatland, The Time Machine, The Island of Doctor Moreau, The Invisible Man,
The War of the Worlds, A Princess of Mars.

**7 фальшивих** (1–2 КБ замість сотень КБ):
```
data/corpus/texts/karel-capek/rur-rossums-universal-robots/original.txt
data/corpus/texts/isaac-asimov/foundation/original.txt
data/corpus/texts/frank-herbert/dune/original.txt
data/corpus/texts/ursula-k-le-guin/rocannons-world/original.txt
data/corpus/texts/ursula-k-le-guin/the-dispossessed/original.txt
data/corpus/texts/william-gibson/neuromancer/original.txt
data/corpus/texts/test-author/test-work/original.txt
```

**7 без тексту:** Solaris, 2001, Ubik, Hyperion, A Fire Upon the Deep,
Blindsight, The Three-Body Problem. **1 сміття:** `The First Starship` (2100).

---

# ЧАСТИНА А — БІБЛІОТЕКА ОРИГІНАЛЬНИХ ТЕКСТІВ

Мета: кожен текст має **чек походження**, за яким будь-хто через рік
повторить завантаження і отримає ті самі байти.

## Т1. Таблиця чеків набуття

Файл `modules/corpus/receipts.py`:

```sql
CREATE TABLE IF NOT EXISTS acquisition_receipts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_slug TEXT NOT NULL,
  edition_id TEXT NOT NULL,
  language TEXT NOT NULL,
  is_translation INTEGER NOT NULL DEFAULT 0,
  source_url TEXT,
  http_status INTEGER,
  fetched_at_utc TEXT NOT NULL,
  raw_sha256 TEXT,
  raw_bytes INTEGER,
  clean_sha256 TEXT,
  clean_bytes INTEGER,
  newline_policy TEXT DEFAULT 'LF',
  transform_id TEXT,
  transform_sha256 TEXT,
  rights TEXT NOT NULL,
  rights_basis TEXT,
  acquisition_class TEXT NOT NULL
    CHECK (acquisition_class IN ('verified','synthetic','unsourced','absent')),
  note TEXT,
  UNIQUE (work_slug, edition_id)
);
```

- `edition_id` — звідки саме, напр. `gutenberg:35`.
- `language` — мова САМОГО ФАЙЛУ (`cs`, `en`), не мова автора.
- `is_translation` — 1 переклад, 0 оригінал. Для `robot` доказом є чеський
  оригінал, англійський переклад — **інший свідок**.
- `raw_sha256` — хеш як завантажилось, ДО очищення.
- `transform_sha256` — хеш КОДУ очищення (`inspect.getsource`). Без нього
  очищення невідтворюване і координати попливуть.
- `newline_policy` — завжди `LF` (див. Т0.1).
- `rights_basis` — конкретика, напр. `author died 1938, published 1920, PD`.

**Тест Т1:**
```bash
PYTHONIOENCODING=utf-8 python -c "import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db');print(c.execute('select count(*) from acquisition_receipts').fetchone())"
```
Друкує `(0,)` без помилки.

## Т2. Карантин фальшивих файлів

Для кожного з 7 шляхів — запис: `acquisition_class='synthetic'`,
`rights='unknown'`, `note='LLM-generated pastiche, not authentic. Quarantined <дата>.'`
Для R.U.R. додати в `note`: `Cyrillic U+043A/U+0430 inside Czech word`.

```sql
UPDATE works SET has_full_text=0, research_status='quarantined' WHERE slug IN (...);
```

**Файли не видаляй.** Перейменуй `original.txt` → `original.QUARANTINE.txt`.
Видали запис `The First Starship`.

**Тест Т2:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('synthetic:',c.execute(\"select count(*) from acquisition_receipts where acquisition_class='synthetic'\").fetchone()[0])
print('full text:',c.execute('select count(*) from works where has_full_text=1').fetchone()[0])
print('First Starship:',c.execute(\"select count(*) from works where title_orig like '%First Starship%'\").fetchone()[0])
"
```
Очікується `synthetic: 7`, `full text: 10`, `First Starship: 0`.

## Т3. Ретро-чеки для 10 справжніх текстів

Для кожного: взяти `gutenberg_id` з `PUBLIC_DOMAIN_SF_MASTERS`; завантажити
заново; `raw_sha256`; прогнати очищення з нормалізацією LF; `clean_sha256`;
порівняти з файлом на диску.

Розбіжність запиши чесно: `acquisition_class='verified'` +
`note='clean_sha mismatch; on-disk replaced from source'` і перезапиши файл.
**Не підганяй.** Gutenberg оновлює тексти — розбіжність нормальна.

**Тест Т3:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('verified:',c.execute(\"select count(*) from acquisition_receipts where acquisition_class='verified'\").fetchone()[0])
print('без raw_sha256:',c.execute('select count(*) from acquisition_receipts where raw_sha256 is null').fetchone()[0])
"
```
Очікується `verified: 10`, `без raw_sha256: 0`.

## Т4. Повернути R.U.R. по-справжньому

R.U.R. (1920) — суспільне надбання. На Gutenberg є щонайменше `59112` і
`13083`. **Перевір, який з них якою мовою** — завантаж обидва, глянь перші
500 символів, визнач мову.

Окремий чек на кожну редакцію: чеський оригінал → `language='cs'`,
`is_translation=0`; англійський переклад → `language='en'`, `is_translation=1`.

Немає чеського на Gutenberg → `acquisition_class='absent'`,
`note='Czech original not found on Gutenberg; checked <дата>'`.
**Не підставляй переклад замість оригіналу мовчки.**

**Тест Т4:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
for r in c.execute(\"select edition_id,language,is_translation,acquisition_class from acquisition_receipts where work_slug like 'rur%'\"): print(r)
"
```

## Т5. Розширення суспільним надбанням

Кандидати — **статус ПЕРЕВІРИТИ, не вважати даним**:
```
Wells         The First Men in the Moon (1901), When the Sleeper Wakes (1899)
Verne         Around the Moon (1870), Robur the Conqueror (1886)
Burroughs     The Gods of Mars (1913), The Land That Time Forgot (1918)
Bellamy       Looking Backward (1888)
Butler        Erewhon (1872)
Bulwer-Lytton The Coming Race (1871)
Gilman        Herland (1915)
Forster       The Machine Stops (1909)
Cavendish     The Blazing World (1666)
Voltaire      Micromégas (1752)
```
Знайти ID → перевірити права → заповнити `rights_basis` → завантажити.
Не знайшов або статус неясний → `absent` + `note`.
**Не додавай твір, статус якого не підтвердив.**

**Тест Т5:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
for r in c.execute('select acquisition_class,count(*) from acquisition_receipts group by 1'): print(r)
print('без rights_basis:',c.execute(\"select count(*) from acquisition_receipts where acquisition_class='verified' and (rights_basis is null or rights_basis='')\").fetchone()[0])
"
```
Очікується `без rights_basis: 0`.

## Т6. Твори в копірайті — НЕ завантажувати

Dune, Neuromancer, Foundation, Solaris, Hyperion, Ubik, 2001, Blindsight,
Three-Body, The Dispossessed, Rocannon's World.

Чек: `acquisition_class='absent'`, `rights='in_copyright'`,
`rights_basis='published <рік>, author <ім'я>, still under copyright'`,
`note='full text intentionally NOT acquired'`.

Це свідоме рішення, і воно має бути записане.

**Тест Т6:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('in_copyright:',c.execute(\"select count(*) from acquisition_receipts where rights='in_copyright'\").fetchone()[0])
print('ПОРУШЕННЯ:',c.execute(\"select count(*) from acquisition_receipts where rights='in_copyright' and clean_sha256 is not null\").fetchone()[0])
"
```
Друге число має бути `0`.

## Т7. Каталог бібліотеки

`modules/corpus/catalog_report.py` → `docs/LIBRARY_CATALOG.md`:

| Твір | Рік | Мова | Оригінал/переклад | Клас | Слів | Джерело | Права |

Підсумок: усього / з повним текстом / відсутні через копірайт / у карантині /
не знайдено / загальний обсяг у символах.

---

# ЧАСТИНА Б — СВІДКИ

**Ми не зберігаємо цитати. Ми зберігаємо координати.** Цитата — результат
читання файлу за адресою «файл X, з байта N, довжиною L». Вигадати таку
координату неможливо: якщо байти не ті, перевірка падає.

## Т8. Таблиця свідків

Схему розширено за Д6 і Д7 — поля одразу в `CREATE TABLE`, не через `ALTER`.

```sql
CREATE TABLE IF NOT EXISTS attestations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  term_id INTEGER REFERENCES terms(id) ON DELETE CASCADE,
  term_orig TEXT NOT NULL,
  work_id INTEGER,
  year INTEGER,
  register TEXT NOT NULL CHECK (register IN ('attested','external','proposed')),
  zone TEXT,
  matched_form TEXT,

  cts_urn TEXT,
  artifact_sha256 TEXT,
  byte_start INTEGER,
  byte_len INTEGER,
  window_sha256 TEXT,

  authority TEXT,
  authority_url TEXT,
  authority_snapshot_sha256 TEXT,
  retrieved_at_utc TEXT,

  proposed_ukr_term TEXT,
  grinchenko_root TEXT,
  derivation_model TEXT,
  stylistic_note TEXT,
  root_attested_in_grinchenko INTEGER DEFAULT 0,

  verified_at_utc TEXT,
  verifier_version TEXT,
  proposed_by_model TEXT,

  CHECK (
    (register='attested' AND cts_urn IS NOT NULL AND artifact_sha256 IS NOT NULL
      AND byte_start IS NOT NULL AND byte_len IS NOT NULL AND window_sha256 IS NOT NULL)
    OR (register='external' AND authority IS NOT NULL AND authority_snapshot_sha256 IS NOT NULL)
    OR (register='proposed' AND cts_urn IS NULL AND artifact_sha256 IS NULL
      AND proposed_ukr_term IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_attestations_lookup
  ON attestations(term_orig, register, zone);
```

Три регістри:
- `attested` — знайшли у своєму файлі, є координата;
- `external` — тексту нема, є авторитетне джерело (HD SF) і знімок сторінки;
- `proposed` — наша українська пропозиція; свідка нема й бути не може.

`root_attested_in_grinchenko` — `0`, доки людина не звірить зі справжнім
оцифрованим словником. Ти цього не робиш.

**Тест Т8:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
for label,sql in [
 ('attested без свідка',\"insert into attestations(term_orig,register) values('x','attested')\"),
 ('proposed без укр. терміна',\"insert into attestations(term_orig,register) values('x','proposed')\")]:
    try:
        c.execute(sql); print('ПОМИЛКА, CHECK не спрацював:',label)
    except sqlite3.IntegrityError: print('OK, відхилено:',label)
c.rollback()
"
```
Обидва рядки мають бути `OK, відхилено`.

## Т9. Пошук і свідок — `modules/corpus/witness.py`

Три частини. Друга і третя — виправлені проти доповнення Д2–Д4.

### 9а. Вирівнювання меж UTF-8 (Д2, прийнято як є)

Без нього вікно може обрізати чеську `č` або кирилицю посередині символу, і
валідний свідок хибно відхиляється як `decode_error`.

```python
def snap_to_utf8_boundary(data: bytes, pos: int, direction: str = 'backward') -> int:
    if pos <= 0 or pos >= len(data):
        return max(0, min(pos, len(data)))
    while pos > 0 and (data[pos] & 0xC0) == 0x80:   # 10xxxxxx = байт продовження
        if direction == 'backward':
            pos -= 1
        else:
            pos += 1
            if pos >= len(data):
                break
    return pos
```
Перевірено на всіх позиціях рядка `člověka robot ženě` — 0 падінь.

### 9б. Пошук форм слова (ВИПРАВЛЕНО проти Д3 і Д4)

У доповненні пропонувався regex по БАЙТАХ із `\b` та `IGNORECASE`. Так робити
не можна: у байтовому режимі і `\b`, і згортання регістру працюють лише для
ASCII. Перевірено — чеське `robotů` дає **0 збігів**, українське `мережище`
дає **0 збігів**, англійська множина `morlocks` пропускається.

Правильно — шукати в ДЕКОДОВАНОМУ тексті, потім переводити зсув символів у
зсув байтів:

```python
import re

def find_occurrences(data: bytes, term: str, variants=None):
    """Повертає [(byte_offset, знайдена_форма), ...]. Без LLM."""
    text = data.decode('utf-8', errors='replace')
    words = [term] + (variants or [])
    parts = []
    for w in words:
        # пробіл або дефіс у терміні = будь-який пробіл, дефіс АБО розрив рядка
        parts.append(r'[-\s]+'.join(re.escape(t) for t in re.split(r'[-\s]+', w)))
    pattern = r'\b(?:' + '|'.join(parts) + r')\w*'
    out = []
    for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.UNICODE):
        out.append((len(text[:m.start()].encode('utf-8')), m.group()))
    return out
```

Це одночасно закриває і Д4. Претензія Д4 про переноси через дефіс емпірично
слабка — у 10 книгах знайдено лише **2** таких переноси. Але **37 487**
звичайних розривів рядка між словами: багатослівний термін `time machine`
регулярно розірваний як `time\nmachine`. Нормалізатор `[-\s]+` ловить обидва.

Перевірено: чеські відмінки `Roboti/Robotů/roboty` — 3 з 3; українські
регістри — 3 з 3; англійська множина — 3 з 3; `time\nmachine`, `heat-ray`,
`heat-\nray` — знайдено всі.

Знайдену форму записуй у `matched_form` — свідок фіксує саме ту форму,
що реально є в тексті.

### 9в. Побудова і перевірка свідка

```python
import hashlib

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def build_witness(path, term, occurrence_index=0, pad=80, length=200, variants=None):
    data = open(path, 'rb').read()
    found = find_occurrences(data, term, variants)
    if occurrence_index >= len(found):
        return None
    i, form = found[occurrence_index]
    start = snap_to_utf8_boundary(data, max(0, i - pad), 'backward')
    end   = snap_to_utf8_boundary(data, min(len(data), start + length), 'forward')
    window = data[start:end]
    return {
        "artifact_sha256": sha256_bytes(data),
        "byte_start": start,
        "byte_len": len(window),
        "window_sha256": sha256_bytes(window),
        "matched_form": form,
        "occurrences_total": len(found),
    }

def verify_witness(w, path, term):
    """П'ять перевірок. Усі бінарні. Ніяких ваг і порогів."""
    data = open(path, 'rb').read()
    if sha256_bytes(data) != w["artifact_sha256"]:
        return ("REJECT", "artifact_drift", None)
    window = data[w["byte_start"]: w["byte_start"] + w["byte_len"]]
    if len(window) != w["byte_len"]:
        return ("REJECT", "short_read", None)
    if sha256_bytes(window) != w["window_sha256"]:
        return ("REJECT", "window_mismatch", None)
    try:
        text = window.decode('utf-8')
    except UnicodeDecodeError:
        return ("REJECT", "decode_error", None)
    if term and term.lower() not in text.lower():
        return ("REJECT", "term_absent", None)
    return ("ACCEPT", "ok", text)
```

### 9г. Рендеринг цитати (ВИПРАВЛЕНО проти Д8)

У доповненні `render_quote` повертає рядок `"[CORRUPTED WITNESS: ...]"`.
Так робити не можна: такий рядок може мовчки потрапити у науковий експорт
і виглядати там як цитата. Fail-closed означає виняток, а не заглушку.

```python
class WitnessCorrupted(Exception):
    pass

def render_quote(witness: dict, file_path: str, term: str = "") -> str:
    status, reason, text = verify_witness(witness, file_path, term)
    if status != "ACCEPT":
        raise WitnessCorrupted(f"{reason} @ {file_path}:{witness.get('byte_start')}")
    return text.strip()
```
Викликач мусить обробити виняток свідомо. Мовчазної підстановки не буває.

**Тест Т9** — `test_witness.py`:
```python
def test_roundtrip():
    w = build_witness(TM_PATH, "Morlock")
    assert verify_witness(w, TM_PATH, "Morlock")[0] == "ACCEPT"

def test_shift_one_byte_rejected():
    w = build_witness(TM_PATH, "Morlock"); w["byte_start"] += 1
    assert verify_witness(w, TM_PATH, "Morlock")[0] == "REJECT"

def test_fake_coordinate_rejected():
    w = build_witness(TM_PATH, "Morlock"); w["byte_start"] = 9_999_999
    assert verify_witness(w, TM_PATH, "Morlock")[0] == "REJECT"

def test_plural_and_case_found():
    data = "The Morlock and morlocks and MORLOCK.".encode('utf-8')
    assert len(find_occurrences(data, "morlock")) == 3

def test_czech_inflections_found():
    data = "Roboti pracují. Robotů bylo mnoho. roboty zde.".encode('utf-8')
    assert len(find_occurrences(data, "robot")) == 3

def test_multiword_across_newline():
    assert len(find_occurrences(b"a time\nmachine here", "time machine")) == 1

def test_corrupted_raises():
    w = build_witness(TM_PATH, "Morlock"); w["window_sha256"] = "0"*64
    try:
        render_quote(w, TM_PATH); assert False
    except WitnessCorrupted:
        pass
```
Усі сім зелені.

## Т10. Карта структурних зон (Д5, прийнято)

Проблема реальна: у The Time Machine перше входження `Morlock` — на байті
**484**, і це **зміст книжки**, не текст. Координата правильна, науковий
статус — ні.

Створи `modules/corpus/zones.py` з детермінованим авторозмітником за
маркерами Gutenberg:

1. `front_matter` — від 0 до `*** START OF THE PROJECT GUTENBERG EBOOK ***`
   плюс преамбула видання;
2. `toc` — від `CONTENTS` / `TABLE OF CONTENTS` до першого
   `CHAPTER I` / `BOOK I` / `PART I`;
3. `body` — від першого розділу до `THE END` / `FINIS`;
4. `back_matter` — після `*** END OF THE PROJECT GUTENBERG EBOOK ***`.

Кладе `zones.json` поруч із текстом.

**Обов'язково:** авторозмітку **людина оглядає і підтверджує** мінімум на
3 творах, перш ніж вона піде в датування. Автомат тут помічник, не суддя.
`zones.json` іде під печатку нарівні з текстом — зміна меж зон змінює
наукове твердження.

Правило: у датуванні беруть участь ТІЛЬКИ свідки із зони `body`. Свідки з
`toc` зберігаються з `zone='toc'` і в датування не входять.

**Тест Т10:** свідок `Morlock` з `byte_start=484` у The Time Machine отримує
`zone='toc'` і не потрапляє в датування.

## Т11. Найраніша атестація — запит, а не поле

Видали `terms.first_attestation_year`.

```sql
CREATE VIEW IF NOT EXISTS earliest_attestation AS
SELECT term_orig,
       MIN(year) AS earliest_year,
       COUNT(*)  AS witness_count
FROM attestations
WHERE register='attested' AND zone='body' AND verified_at_utc IS NOT NULL
GROUP BY term_orig;
```

Раніше рік копіювали з року книжки — через це `cyberspace` записано роком
1982, а прив'язано до Neuromancer 1984. Тепер рік обчислюється зі свідків і
сам виправиться, коли в корпус додадуть потрібний текст.

У КОЖНОМУ звіті: «найраніша засвідчена поява в нашому корпусі станом на
\<дата\>». Ніколи — «перша поява у світовій літературі».

## Т12. Перевернути цикл

```
КРОК 1  ПРОПОЗИЦІЯ   LLM читає шматок і називає лише СПИСОК СЛІВ-КАНДИДАТІВ.
                     Ніяких цитат. Модель може помилятися — це безпечно.
КРОК 2  ЛОКАЛІЗАЦІЯ  Код (не модель) шукає через find_occurrences() у ПОВНОМУ
                     тексті і будує свідка. Нема збігу — кандидата геть.
КРОК 3  ДЕРИВАЦІЯ    LLM отримує ВЖЕ ЗНАЙДЕНУ справжню цитату і пропонує
                     український відповідник. register='proposed'.
```

Прибрати `raw_text[:1800]`. Читати весь текст вікнами по 8000 символів із
перекриттям 200. Прибрати позначку `analyzed` після одного терміна.

Модель: `num_predict` з 700 → 2000 (зараз відповідь обривається і JSON не
парситься — усі 4 запуски впали саме так). Брати `qwen3.5:27b`, не
`qwen3.6:35b` — другий займає 23.9 ГБ на картці 24 ГБ і йде в таймаут.

**Тест Т12:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('committed:',c.execute(\"select count(*) from research_cycles where status='committed'\").fetchone()[0])
print('attested:',c.execute(\"select count(*) from attestations where register='attested'\").fetchone()[0])
"
```
Зараз `committed: 0`. Після Т12 має бути більше нуля.

## Т13. Полагодити морфологічну перевірку

Зараз працює навпаки:
```
''            → 0.85 ПРИЙНЯТО      ← порожній рядок
'12345'       → 0.85 ПРИЙНЯТО      ← цифри
'мислитель'   → 0.50 ВІДХИЛЕНО     ← нормальне українське слово
'вчитель'     → 0.50 ВІДХИЛЕНО     ← нормальне українське слово
```
Причини: старт 0.85 і тільки вгору; росіянізм шукається підрядком `тель`,
а він є у звичайних українських словах.

Полагодь: старт 0.0, бали лише за доведені ознаки; порожнє/цифри/латиниця →
0.0; слово має бути з українських літер (з `ґ`, `є`, `і`, `ї`, апостроф);
прибери підрядковий `тель` — або звузь до повного співпадіння зі списком.

**Тест Т13:**
```python
def test_rejects_junk():
    for j in ['', '12345', 'asdfgh', 'qwerty']:
        assert GrinchenkoEngine.evaluate_ukrainian_neologism(j,'')['is_acceptable'] is False

def test_accepts_real():
    for g in ['мислитель','вчитель','Миттєвісник','провісник']:
        assert GrinchenkoEngine.evaluate_ukrainian_neologism(g,'')['is_acceptable'] is True
```

## Т14. Старі 5 термінів — у чесний стан

`robot`, `cyberspace`, `ansible`, `psychohistory`, `mentat` — цитати вигадані.
Доведено: для `ansible` професійний словник HD SF дає «Noting the coordinates
at which the ansible sender was set…», а в базі записано зовсім інший текст.

1. Українські варіанти → `register='proposed'`, у `proposed_ukr_term`.
   Вони не стають недійсними — вони просто пропозиції.
2. Англійські цитати → **видалити**. Не переписувати, не «уточнювати».
3. Посилання на Грінченка → `root_attested_in_grinchenko = 0`.
4. Де є текст у корпусі — побудувати справжнього свідка `build_witness()`.

**Тест Т14:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('вигаданих цитат:',c.execute(\"select count(*) from terms where original_context is not null and original_context!=''\").fetchone()[0])
"
```
Очікується `0`.

---

# ЯК ЗВІТУВАТИ

```
ЗАДАЧА: Т3
ЗРОБЛЕНО: ретро-чеки для 10 творів
ТЕСТ: verified: 10, без raw_sha256: 0 — ЗЕЛЕНИЙ
ПРОБЛЕМИ: у 2 творів clean_sha не збігся, файли перезаписано з джерела
NOT_FOUND: —
```

Не вийшло — пиши `ПРОБЛЕМИ` чесно і зупиняйся. **Не обходь перешкоду
вигадуванням даних.** Краще зупинена задача, ніж заповнена неправдою база.

---

# РОЗБІР ДОПОВНЕННЯ Д0–Д8

| | Вердикт | Підстава |
| --- | --- | --- |
| Д0 PowerShell | прийнято | `export` тут дає `CommandNotFoundException` |
| Д1 CRLF/хеші | прийнято з правкою | правила за розширенням лишали дірку: 11 із 17 шляхів корпусу — `.md`; замінено на правила за шляхом |
| Д2 UTF-8 snap | прийнято як є | 0 падінь на всіх позиціях `člověka robot ženě` |
| Д3 флексії | проблема вірна, код замінено | байтовий `\b`+`IGNORECASE` = ASCII-only: `robotů` 0 збігів, `мережище` 0 збігів, `morlocks` пропущено |
| Д4 дефіси | засновку виправлено | у 10 книгах лише 2 переноси через дефіс, але 37 487 звичайних розривів рядка; нормалізатор `[-\s]+` покриває обидва |
| Д5 авто-зони | прийнято з умовою | людське підтвердження обов'язкове, `zones.json` під печатку |
| Д6 поля `proposed` | прийнято | перевірено: `ALTER ... ADD COLUMN ... CHECK` у SQLite справді діє; але поля внесено одразу в `CREATE TABLE` |
| Д7 `term_id`+`term_orig` | прийнято | розумна денормалізація, індекс додано |
| Д8 `render_quote` | прийнято з правкою | заглушка-рядок могла потрапити в експорт як цитата; замінено на виняток |

---

# КОРОТКО, ЯКЩО ЗАБУВ

1. Спочатку Т0 (кодування) і Т0.1 (CRLF). Інакше все інше — марно.
2. Тексти — тільки завантажені. Ніколи не написані тобою.
3. Цитати — тільки прочитані з файлу за координатою.
4. Не знаєш — `NULL` або `NOT_FOUND`, не «схоже на правду».
5. Кожен файл у бібліотеці має чек походження.
6. `attested` = є файл і координата. `external` = чуже джерело.
   `proposed` = наша пропозиція, свідка нема й не треба.
7. «Найраніша в нашому корпусі», ніколи «перша поява».
8. Тест червоний → зупинись.
