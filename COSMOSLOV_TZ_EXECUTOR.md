# ТЗ для виконавця — Космослов

Ти виконавець. Тобі дають задачі Т1…Т14. Роби їх ПО ЧЕРЗІ.
Після кожної задачі запусти її тест приймання. Якщо тест червоний — не йди далі.

Робоча тека: `C:\ai_server\the _best_book`
База: `data\scifi_lexicon.db`
Бібліотека текстів: `K:\scifi_library\authors\<автор>\<твір>\`

---

## Т0. ЗРОБИ ЦЕ ПЕРШИМ (інакше всі тести будуть «червоні» без причини)

Консоль Windows тут у кодуванні cp1252 і **падає на українських літерах**.
Ти побачиш `UnicodeEncodeError: 'charmap' codec can't encode` і подумаєш,
що тест не пройшов. Це не так — це кодування консолі, а не помилка коду.

Перед КОЖНОЮ сесією роботи виконай:

```bash
export PYTHONIOENCODING=utf-8
```

Або додавай префікс до кожної команди:
```bash
PYTHONIOENCODING=utf-8 python -c "..."
```

Перевірка, що працює:
```bash
PYTHONIOENCODING=utf-8 python -c "print('українські літери — ок')"
```
Має надрукувати текст без traceback.

**Якщо бачиш `UnicodeEncodeError` — це Т0, а не твоя помилка в задачі.
Не «лагодь» код, не переписуй тести українською латиницею.**

---

## ГОЛОВНЕ ПРАВИЛО

**Ти ніколи не пишеш текст художнього твору сам. Ніколи не пишеш цитату сам.
Ніколи не пишеш номер тому чи сторінки словника сам.**

Якщо тобі бракує тексту — ти не додумуєш. Ти записуєш `NOT_FOUND` і йдеш далі.

Причина: у цьому проєкті вже сталася аварія. Хтось згенерував «оригінальні
тексти» замість того, щоб їх завантажити. У чеському слові `člověka` виявили
кирилічні літери `к` і `а` — так пише мовна модель, так не пише жоден скан.
Через це 6 файлів і 5 словникових статей — недійсні. Твоє завдання —
прибрати наслідки, а не додати нових.

### 7 заборон (порушення = зупинка роботи)

1. Не вигадувати текст твору. Не «відновлювати по пам'яті». Не переказувати.
2. Не вигадувати цитат. Цитата береться ТІЛЬКИ читанням файлу з диска.
3. Не вигадувати посилань на словник Грінченка (том, сторінка).
4. Не заповнювати порожнє поле «правдоподібним» значенням. Порожнє = `NULL`.
5. Не видаляти й не редагувати наявні файли текстів. Тільки позначати.
6. Не змінювати поріг, вагу чи критерій після того, як побачив результат.
7. Не писати «перша поява». Писати «найраніша знайдена в нашому корпусі».

---

## ЩО ВЖЕ Є (не переробляй)

Робочий код, який МОЖНА і ТРЕБА використовувати:

| Файл | Що дає |
| --- | --- |
| `modules/corpus/harvester.py` | `fetch_from_gutenberg(id)`, `clean_gutenberg_text(txt)` — працює |
| `modules/corpus/manager.py` | `search_term_context(text, term)` — детермінований пошук, працює |
| `modules/corpus/manager.py` | `package_llm_ready_work(...)` — розкладка на NAS, працює |
| `core/db.py` | `DatabaseManager.get_connection()` — працює |

Зламаний код, який буде ЗАМІНЕНО (поки не чіпай):

| Файл | Проблема |
| --- | --- |
| `modules/autoresearch/evaluator.py` | пропускає вигадані цитати з оцінкою 0.91 |
| `modules/autoresearch/loop.py` | читає тільки перші 1800 символів = 0.7% корпусу |
| `modules/lexicography/grinchenko_engine.py` | приймає `12345`, відхиляє `мислитель` |

---

## СТАН КОРПУСУ

**10 файлів справжні** (завантажені з Project Gutenberg, 30–100 тис. слів):
Frankenstein, Journey to the Centre of the Earth, From the Earth to the Moon,
Twenty Thousand Leagues, Flatland, The Time Machine, The Island of Doctor
Moreau, The Invisible Man, The War of the Worlds, A Princess of Mars.

**7 файлів фальшиві** (згенеровані моделлю, 1–2 КБ замість сотень КБ):

```
data/corpus/texts/karel-capek/rur-rossums-universal-robots/original.txt
data/corpus/texts/isaac-asimov/foundation/original.txt
data/corpus/texts/frank-herbert/dune/original.txt
data/corpus/texts/ursula-k-le-guin/rocannons-world/original.txt
data/corpus/texts/ursula-k-le-guin/the-dispossessed/original.txt
data/corpus/texts/william-gibson/neuromancer/original.txt
data/corpus/texts/test-author/test-work/original.txt
```

**7 творів без тексту взагалі:** Solaris, 2001, Ubik, Hyperion, A Fire Upon
the Deep, Blindsight, The Three-Body Problem.

**1 сміття:** запис `The First Starship` (рік 2100) — залишок від тесту.

---

# ЧАСТИНА А — БІБЛІОТЕКА ОРИГІНАЛЬНИХ ТЕКСТІВ

Локальна бібліотека — це фундамент. Без неї перевірити нічого не можна.
Мета: кожен текст у бібліотеці має **чек походження**, за яким будь-хто
через рік може повторити завантаження і отримати ті самі байти.

## Т1. Таблиця чеків набуття

Створи файл `modules/corpus/receipts.py`. У ньому — створення таблиці:

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

Пояснення полів простими словами:
- `edition_id` — звідки саме, напр. `gutenberg:35`.
- `language` — мова САМОГО ФАЙЛУ (`cs`, `en`, `fr`…), не мова автора.
- `is_translation` — 1 якщо це переклад, 0 якщо оригінал. Це важливо:
  для терміна `robot` доказом є чеський оригінал, а не англійський переклад.
- `raw_sha256` — хеш файлу ЯК ЗАВАНТАЖИВСЯ, до будь-якого очищення.
- `clean_sha256` — хеш після `clean_gutenberg_text`.
- `transform_sha256` — хеш КОДУ функції очищення (`inspect.getsource`).
  Без нього не можна повторити очищення і байтові координати «попливуть».
- `rights_basis` — чому вважаємо суспільним надбанням, напр.
  `author died 1938, work published 1920, PD in source country`.

**Тест приймання Т1:**
```bash
PYTHONIOENCODING=utf-8 python -c "import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db');print(c.execute('select count(*) from acquisition_receipts').fetchone())"
```
Має надрукувати `(0,)` без помилки.

---

## Т2. Карантин фальшивих файлів

Для кожного з 7 фальшивих шляхів (список вище) додай запис:

- `acquisition_class = 'synthetic'`
- `rights = 'unknown'`
- `note = 'LLM-generated pastiche, not an authentic text. Quarantined YYYY-MM-DD.'`
- для R.U.R. додатково: `note` містить `Cyrillic U+043A/U+0430 inside Czech word`

Далі познач у таблиці `works`:
```sql
UPDATE works SET has_full_text = 0, research_status = 'quarantined'
WHERE slug IN (...7 slug'ів...);
```

**Файли НЕ видаляй.** Перейменуй теку `original.txt` → `original.QUARANTINE.txt`,
щоб жоден код їх випадково не прочитав.

Також прибери сміття: видали запис `The First Starship` з `works`.

**Тест приймання Т2:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('synthetic receipts:',c.execute(\"select count(*) from acquisition_receipts where acquisition_class='synthetic'\").fetchone()[0])
print('works with full text:',c.execute('select count(*) from works where has_full_text=1').fetchone()[0])
print('First Starship left:',c.execute(\"select count(*) from works where title_orig like '%First Starship%'\").fetchone()[0])
"
```
Очікується: `synthetic receipts: 7`, `works with full text: 10`, `First Starship left: 0`.

---

## Т3. Ретро-чеки для 10 справжніх текстів

Ці файли вже на диску, але без чеків. Для кожного:

1. Візьми `gutenberg_id` зі списку `PUBLIC_DOMAIN_SF_MASTERS` у `harvester.py`.
2. Завантаж заново через `fetch_from_gutenberg(id)`.
3. Порахуй `raw_sha256` завантаженого.
4. Прогони `clean_gutenberg_text`, порахуй `clean_sha256`.
5. Порівняй `clean_sha256` з хешем файлу, що вже лежить на диску.

Результат порівняння запиши чесно:
- збіглося → `acquisition_class='verified'`
- не збіглося → `acquisition_class='verified'`, але `note='clean_sha mismatch
  with on-disk file; on-disk replaced from source'` і перезапиши файл з джерела.

Не «підганяй» результат. Розбіжність — нормальна річ (Gutenberg оновлює тексти).

**Тест приймання Т3:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
r=c.execute(\"select count(*) from acquisition_receipts where acquisition_class='verified'\").fetchone()[0]
n=c.execute('select count(*) from acquisition_receipts where raw_sha256 is null').fetchone()[0]
print('verified:',r,'| без raw_sha256:',n)
"
```
Очікується: `verified: 10`, `без raw_sha256: 0`.

---

## Т4. Повернути R.U.R. по-справжньому

R.U.R. (1920) — суспільне надбання. Фальшивку ми викинули, тепер набудь
справжній текст.

На Project Gutenberg є щонайменше два записи: `59112` і `13083`.
**Твоє завдання — перевірити, який з них якою мовою.** Завантаж обидва,
подивись перші 500 символів, визнач мову.

Заведи ОКРЕМИЙ чек на кожну знайдену редакцію:
- чеський оригінал → `language='cs'`, `is_translation=0`
- англійський переклад → `language='en'`, `is_translation=1`

Якщо чеського оригіналу на Gutenberg немає — так і запиши:
`acquisition_class='absent'`, `note='Czech original not found on Gutenberg;
checked <дата>'`. Не підставляй переклад замість оригіналу мовчки.

**Тест приймання Т4:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
for r in c.execute(\"select edition_id,language,is_translation,acquisition_class from acquisition_receipts where work_slug like 'rur%'\"): print(r)
"
```
Очікується щонайменше один рядок; поле `language` заповнене реальною мовою.

---

## Т5. Розширення бібліотеки — суспільне надбання

Знайди і додай ще твори, що є суспільним надбанням. Кандидати для перевірки
(**статус треба ПЕРЕВІРИТИ, не вважати даним**):

```
Wells        The First Men in the Moon (1901), When the Sleeper Wakes (1899)
Verne        Around the Moon (1870), Robur the Conqueror (1886)
Burroughs    The Gods of Mars (1913), The Land That Time Forgot (1918)
Bellamy      Looking Backward (1888)
Butler       Erewhon (1872)
Bulwer-Lytton The Coming Race (1871)
Gilman       Herland (1915)
Forster      The Machine Stops (1909)
Cavendish    The Blazing World (1666)
Voltaire     Micromégas (1752)
```

Для кожного:
1. Знайди на `gutenberg.org`, візьми ID.
2. Перевір статус прав. Заповни `rights_basis` конкретикою.
3. Якщо не знайшов або статус неясний → `acquisition_class='absent'` + `note`.
4. Якщо знайшов → завантаж, чек, розклади через `package_llm_ready_work`.

**Не додавай твір, статус якого ти не зміг підтвердити.** Порожньо краще,
ніж неправильно.

**Тест приймання Т5:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
for r in c.execute('select acquisition_class,count(*) from acquisition_receipts group by 1'): print(r)
print('без rights_basis:',c.execute(\"select count(*) from acquisition_receipts where acquisition_class='verified' and (rights_basis is null or rights_basis='')\").fetchone()[0])
"
```
Очікується: `без rights_basis: 0`.

---

## Т6. Твори в копірайті — НЕ завантажувати

Dune, Neuromancer, Foundation, Solaris, Hyperion, Ubik, 2001, Blindsight,
The Three-Body Problem, The Dispossessed, Rocannon's World — ще під
охороною авторського права.

Для кожного заведи чек:
- `acquisition_class='absent'`
- `rights='in_copyright'`
- `rights_basis='published <рік>, author <ім'я>, still under copyright'`
- `note='full text intentionally NOT acquired'`

Це не прогалина, а свідоме рішення. Воно має бути записане, щоб через рік
ніхто не подумав, що просто «забули завантажити».

**Тест приймання Т6:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('in_copyright records:',c.execute(\"select count(*) from acquisition_receipts where rights='in_copyright'\").fetchone()[0])
print('порушення (є текст при копірайті):',c.execute(\"select count(*) from acquisition_receipts where rights='in_copyright' and clean_sha256 is not null\").fetchone()[0])
"
```
Очікується: друге число = `0`.

---

## Т7. Каталог бібліотеки — звіт

Створи `modules/corpus/catalog_report.py`, що друкує і зберігає у
`docs/LIBRARY_CATALOG.md` таблицю:

| Твір | Рік | Мова | Оригінал/переклад | Клас | Слів | Джерело | Права |

Плюс підсумок:
```
Усього творів у каталозі:        N
З перевіреним повним текстом:    N
Відсутні через копірайт:         N
У карантині (синтетика):         N
Не знайдено:                     N
Загальний обсяг корпусу:         N символів
```

**Тест приймання Т7:** файл `docs/LIBRARY_CATALOG.md` існує, числа в підсумку
збігаються з `SELECT` по базі.

---

# ЧАСТИНА Б — СВІДКИ (доказова база)

Головна ідея: **ми не зберігаємо цитати. Ми зберігаємо координати.**

Цитата — це не текст у базі, а результат читання файлу за адресою
«файл X, з байта 214880, довжиною 160 байтів». Хто завгодно може відкрити
файл і перевірити. Вигадати таку координату неможливо: якщо байти за нею не
ті, перевірка падає.

## Т8. Таблиця свідків

```sql
CREATE TABLE IF NOT EXISTS attestations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  term_orig TEXT NOT NULL,
  work_id INTEGER,
  year INTEGER,
  register TEXT NOT NULL CHECK (register IN ('attested','external','proposed')),
  zone TEXT,
  cts_urn TEXT,
  artifact_sha256 TEXT,
  byte_start INTEGER,
  byte_len INTEGER,
  window_sha256 TEXT,
  authority TEXT,
  authority_url TEXT,
  authority_snapshot_sha256 TEXT,
  retrieved_at_utc TEXT,
  verified_at_utc TEXT,
  verifier_version TEXT,
  proposed_by_model TEXT,
  CHECK (
    (register='attested' AND cts_urn IS NOT NULL AND artifact_sha256 IS NOT NULL
      AND byte_start IS NOT NULL AND byte_len IS NOT NULL AND window_sha256 IS NOT NULL)
    OR (register='external' AND authority IS NOT NULL AND authority_snapshot_sha256 IS NOT NULL)
    OR (register='proposed' AND cts_urn IS NULL AND artifact_sha256 IS NULL)
  )
);
```

Три регістри простими словами:
- `attested` — знайшли своїми очима у своєму файлі. Є координата.
- `external` — не маємо тексту, але є авторитетне джерело (напр. словник
  HD SF). Є посилання і збережений знімок сторінки.
- `proposed` — наша українська пропозиція. Свідка немає і бути не може,
  бо це нове слово, а не знахідка.

`CHECK` не дасть записати `attested` без координати. Це навмисне.

**Тест приймання Т8:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
try:
    c.execute(\"insert into attestations(term_orig,register) values('x','attested')\")
    print('ПОМИЛКА: CHECK не спрацював')
except sqlite3.IntegrityError:
    print('OK: attested без свідка відхилено')
"
```
Має надрукувати `OK`.

---

## Т9. Верифікатор свідка

Створи `modules/corpus/witness.py`:

```python
import hashlib

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def build_witness(path, term, occurrence_index=0, pad=80, length=200):
    """Знаходить term у файлі й повертає координату. БЕЗ LLM."""
    data = open(path, 'rb').read()
    needle = term.encode('utf-8')
    pos, found = -1, []
    while True:
        pos = data.find(needle, pos + 1)
        if pos == -1: break
        found.append(pos)
    if occurrence_index >= len(found):
        return None
    i = found[occurrence_index]
    start = max(0, i - pad)
    window = data[start:start + length]
    return {
        "artifact_sha256": sha256_bytes(data),
        "byte_start": start,
        "byte_len": len(window),
        "window_sha256": sha256_bytes(window),
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
    if term.lower() not in text.lower():
        return ("REJECT", "term_absent", None)
    return ("ACCEPT", "ok", text)
```

**Тест приймання Т9** — створи `test_witness.py`:
```python
def test_witness_roundtrip():
    p = "<шлях до The Time Machine>"
    w = build_witness(p, "Morlock")
    assert verify_witness(w, p, "Morlock")[0] == "ACCEPT"

def test_shift_one_byte_rejected():
    p = "<шлях>"
    w = build_witness(p, "Morlock"); w["byte_start"] += 1
    assert verify_witness(w, p, "Morlock")[0] == "REJECT"

def test_fake_coordinate_rejected():
    p = "<шлях>"
    w = build_witness(p, "Morlock"); w["byte_start"] = 9_999_999
    assert verify_witness(w, p, "Morlock")[0] == "REJECT"
```
Усі три мають бути зелені.

---

## Т10. Карта структурних зон

Проблема, яку вже виявили: у The Time Machine перше входження `Morlock` —
на байті 484, і це **зміст книжки**, а не текст. Координата правильна,
але цитувати зміст як доказ не можна.

Для кожного верифікованого твору побудуй карту зон і поклади поруч
з текстом як `zones.json`:

```json
{"zones": [
  {"kind":"front_matter","byte_start":0,"byte_end":2100},
  {"kind":"toc","byte_start":2100,"byte_end":3400},
  {"kind":"body","byte_start":3400,"byte_end":184100},
  {"kind":"back_matter","byte_start":184100,"byte_end":184958}
]}
```

Як визначати межі — простими евристиками (рядки `CONTENTS`, `CHAPTER I`,
`THE END`), результат перевіряй очима на 2–3 творах.

Правило: у датуванні враховуються ТІЛЬКИ свідки із зони `body`.
Свідки із `toc` зберігаються з `zone='toc'` і в датуванні не беруть участі.

**Тест приймання Т10:** для The Time Machine свідок `Morlock` з `byte_start=484`
має отримати `zone='toc'` і не потрапити в датування.

---

## Т11. Найраніша атестація — це запит, а не поле

Видали поле `terms.first_attestation_year`. Замість нього:

```sql
CREATE VIEW IF NOT EXISTS earliest_attestation AS
SELECT term_orig,
       MIN(year) AS earliest_year,
       COUNT(*)  AS witness_count
FROM attestations
WHERE register='attested' AND zone='body' AND verified_at_utc IS NOT NULL
GROUP BY term_orig;
```

Чому так: раніше рік просто копіювали з року книжки. Через це вийшла
помилка — `cyberspace` записали роком 1982, а прив'язали до Neuromancer
1984 року. Тепер рік обчислюється зі знайдених свідків і сам виправиться,
коли в корпус додадуть потрібний текст.

У КОЖНОМУ звіті писати саме так:
> найраніша засвідчена поява в нашому корпусі станом на \<дата\>

Ніколи не писати «перша поява у світовій літературі».

**Тест приймання Т11:** `SELECT * FROM earliest_attestation` виконується,
поля `first_attestation_year` у `terms` більше немає.

---

## Т12. Перевернути цикл дослідження

Зараз модель робить усе одразу і тому вигадує. Розділи на три кроки:

```
КРОК 1  ПРОПОЗИЦІЯ
        LLM читає шматок тексту і називає тільки СПИСОК СЛІВ-КАНДИДАТІВ.
        Ніяких цитат. Ніяких пояснень. Просто слова.
        Модель може помилятися скільки завгодно — це безпечно.

КРОК 2  ЛОКАЛІЗАЦІЯ
        Код (не модель!) шукає кожне слово у ПОВНОМУ тексті через
        build_witness(). Немає збігу — кандидата викидаємо мовчки.

КРОК 3  ДЕРИВАЦІЯ
        LLM отримує ВЖЕ ЗНАЙДЕНУ справжню цитату і пропонує український
        відповідник. Записуємо як register='proposed'.
```

Прибери обмеження `raw_text[:1800]` у `loop.py`. Читай увесь текст вікнами
по 8000 символів із перекриттям 200 символів (перекриття потрібне, щоб
слово на межі вікон не загубилося).

Прибери позначення твору `analyzed` після одного терміна — твір готовий,
коли пройдено всі вікна.

Налаштування моделі: `num_predict` підняти з 700 до 2000 (зараз відповідь
обривається на півслові й JSON не парситься — усі 4 запуски впали саме так).
Використовуй `qwen3.5:27b`, не `qwen3.6:35b` — другий займає 23.9 ГБ на
картці 24 ГБ і через це вивалюється в таймаут.

**Тест приймання Т12:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('циклів committed:',c.execute(\"select count(*) from research_cycles where status='committed'\").fetchone()[0])
print('свідків attested:',c.execute(\"select count(*) from attestations where register='attested'\").fetchone()[0])
"
```
Зараз `committed: 0`. Після Т12 має бути більше нуля.

---

## Т13. Полагодити морфологічну перевірку

Зараз `evaluate_ukrainian_neologism` працює навпаки:

```
''            → 0.85 ПРИЙНЯТО      ← порожній рядок!
'12345'       → 0.85 ПРИЙНЯТО      ← цифри!
'asdfgh'      → 0.85 ПРИЙНЯТО
'мислитель'   → 0.50 ВІДХИЛЕНО     ← нормальне українське слово!
'вчитель'     → 0.50 ВІДХИЛЕНО     ← нормальне українське слово!
```

Причини: стартовий бал 0.85 і рухається тільки вгору; перевірка на
росіянізм шукає підрядок `тель`, а він є у звичайних українських словах.

Полагодь:
1. Стартовий бал 0.0, бали ТІЛЬКИ додаються за доведені ознаки.
2. Порожній рядок, цифри, латиниця → 0.0 одразу.
3. Слово має складатися з українських літер (включно з `ґ`, `є`, `і`, `ї`, апостроф).
4. Прибери підрядковий пошук `тель`. Якщо лишаєш перевірку на росіянізми —
   тільки за повним співпадінням слова зі списку, не за підрядком.

**Тест приймання Т13** — новий тест:
```python
def test_morphology_rejects_junk():
    for junk in ['', '12345', 'asdfgh', 'qwerty']:
        assert GrinchenkoEngine.evaluate_ukrainian_neologism(junk,'')['is_acceptable'] is False

def test_morphology_accepts_real_words():
    for good in ['мислитель', 'вчитель', 'Миттєвісник', 'провісник']:
        assert GrinchenkoEngine.evaluate_ukrainian_neologism(good,'')['is_acceptable'] is True
```

---

## Т14. Перевести старі 5 термінів у чесний стан

У базі є 5 термінів (`robot`, `cyberspace`, `ansible`, `psychohistory`,
`mentat`). Їхні цитати — вигадані. Доведено: для `ansible` професійний
словник HD SF дає цитату «Noting the coordinates at which the ansible
sender was set…», а в нашій базі записано зовсім інший текст.

Дії для кожного:
1. Українські варіанти (Тру́дник, Миттєвісник…) → `register='proposed'`.
   Вони не стають недійсними — вони просто пропозиції, а не знахідки.
2. Англійські цитати → **видалити**. Не переписувати, не «уточнювати».
3. Посилання на Грінченка з томом і сторінкою → позначити
   `grinchenko_verified = 0`. Перевірити їх зможе тільки людина за
   справжнім оцифрованим словником.
4. Де є текст у нашому корпусі — побудувати справжнього свідка через
   `build_witness()`.

**Тест приймання Т14:**
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('data/scifi_lexicon.db')
print('вигаданих цитат лишилось:',c.execute(\"select count(*) from terms where original_context is not null and original_context!=''\").fetchone()[0])
"
```
Очікується `0`.

---

# ЯК ЗВІТУВАТИ

Після кожної задачі — короткий блок:

```
ЗАДАЧА: Т3
ЗРОБЛЕНО: ретро-чеки для 10 творів
ТЕСТ: verified: 10, без raw_sha256: 0 — ЗЕЛЕНИЙ
ПРОБЛЕМИ: у 2 творів clean_sha не збігся з диском, файли перезаписано з джерела
NOT_FOUND: —
```

Якщо щось не вийшло — пиши `ПРОБЛЕМИ` чесно і зупиняйся. **Не обходь
перешкоду вигадуванням даних.** Краще зупинена задача, ніж заповнена
неправдою база.

Якщо не можеш знайти текст, статус прав, мову або ID — пиши `NOT_FOUND`
і рухайся далі. Це нормальний результат.

---

# КОРОТКО, ЯКЩО ЗАБУВ

1. Тексти — тільки завантажені. Ніколи не написані тобою.
2. Цитати — тільки прочитані з файлу за координатою.
3. Не знаєш — пиши `NULL` або `NOT_FOUND`, не «схоже на правду».
4. Кожен файл у бібліотеці має чек походження.
5. `attested` = маємо файл і координату. `external` = маємо чуже джерело.
   `proposed` = наша пропозиція, свідка нема й не треба.
6. «Найраніша в нашому корпусі», ніколи «перша поява».
7. Тест червоний → зупинись, не йди далі.
