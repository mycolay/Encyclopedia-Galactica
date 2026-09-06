# Доповнення та інженерні уточнення до ТЗ «Космослов»

**Документ**: `COSMOSLOV_TZ_ADDENDUM.md`  
**Місце розташування**: `C:\ai_server\the _best_book\COSMOSLOV_TZ_ADDENDUM.md`  
**Статус**: Додаток до `COSMOSLOV_TZ_EXECUTOR.md` для окремого розгляду та затвердження.  
**Призначення**: Усунення прихованих пасток операційної системи Windows, кодувань, Unicode-розривів та забезпечення 100% відтворюваності байтових свідків.

---

## Д0. Уточнення Т0 для Windows PowerShell

У Т0 зазначено команди для bash (`export PYTHONIOENCODING=utf-8` або `PYTHONIOENCODING=utf-8 python ...`).
В оболонці Windows PowerShell цей синтаксис викликає `CommandNotFoundException`. 
Для PowerShell правильний синтаксис:

```powershell
$env:PYTHONIOENCODING="utf-8"
```
або однорядковий префікс:
```powershell
$env:PYTHONIOENCODING="utf-8"; python -c "..."
```

---

## Д1. Захист від пастки Windows CRLF (`\r\n`) та дрейфу хешів

### Проблема:
На Windows стандартним закінченням рядка є `\r\n` (CRLF), тоді як Linux і веб-джерела (Project Gutenberg) віддають `\n` (LF).
Якщо файл зберігається або зчитується текстовими інструментами, або якщо Git налаштований з `core.autocrlf=true`, переведення рядків можуть бути автоматично конвертовані. 
У результаті:
1. `artifact_sha256` миттєво зміниться.
2. Усі байтові зміщення `byte_start` після першого рядка «попливуть» на `+1` байт за кожен рядок.
3. Усі раніше верифіковані свідки стануть червоними (`artifact_drift` або `window_mismatch`).

### Інженерне рішення:
1. **Файли корпусу на диску — виключно бінарні**:
   Усі операції запису і читання текстів корпусу (`K:\scifi_library` та `data/corpus/`) здійснювати строго у бінарному режимі (`'rb'` / `'wb'`).
2. **Нормалізація до LF під час очищення**:
   Функція `clean_gutenberg_text` нормалізує всі переводи рядків до єдиного стандарту `\n` (`b'\n'`) **до** обрахунку `clean_sha256` і збереження на диск.
3. **Фіксація в `.gitattributes`**:
   Створити в корені репозиторію файл `.gitattributes`:
   ```gitattributes
   * text=auto eol=lf
   *.txt binary
   *.md text eol=lf
   ```
   Це гарантує, що жоден Git-коміт чи checkout не змінить жодного байта у текстових файлах корпусу.

---

## Д2. Захист від розриву мультибайтових символів UTF-8 у `build_witness`

### Проблема:
У Т9 функція `build_witness` обчислює вікно як:
```python
start = max(0, i - pad)
window = data[start:start + length]
```
Якщо `start` або `start + length` випадково припаде на 2-й, 3-й або 4-й байт символу UTF-8 (наприклад, чеські літери `č`, `ř`, `ě` в *R.U.R.* чи українська кирилиця), виклик `window.decode('utf-8')` у `verify_witness` викличе виняток `UnicodeDecodeError`, і валідний свідок буде помилково відхилений зі статусом `decode_error`.

### Інженерне рішення:
Додати у `modules/corpus/witness.py` функцію автоматичного вирівнювання меж (boundary snap):
```python
def snap_to_utf8_boundary(data: bytes, pos: int, direction: str = 'backward') -> int:
    """Вирівнює байтову позицію на початок UTF-8 кодової точки."""
    if pos <= 0 or pos >= len(data):
        return max(0, min(pos, len(data)))
    # У UTF-8 байти продовження мають бітову маску 10xxxxxx (0x80..0xBF)
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        if direction == 'backward':
            pos -= 1
        else:
            pos += 1
            if pos >= len(data): break
    return pos
```
У `build_witness`:
```python
start = snap_to_utf8_boundary(data, max(0, i - pad), direction='backward')
end = snap_to_utf8_boundary(data, min(len(data), start + length), direction='forward')
window = data[start:end]
```
Це на 100% запобігає появі половинчастих символів без спотворення змісту.

---

## Д3. Регістронезалежність, флексії та множина термінів у `build_witness`

### Проблема:
У Т9 наведено простий пошук:
`needle = term.encode('utf-8')`  
`pos = data.find(needle, pos + 1)`

У реальній класичній літературі:
- Термін може стояти на початку речення з великої літери: *«Robots were moving...»* замість *«robot»*.
- Термін може вживатися у множині: *«Morlocks»*, *«ansibles»*.
- Термін може мати дефісні варіанти: *«time-machine»* проти *«time machine»*, або відмінкові закінчення в чеському оригіналі (*roboty*, *robotů*, *robotům*).
Якщо шукати тільки точний рядок `needle = term.encode('utf-8')`, найраніша згадка на початку речення або у множині буде пропущена.

### Інженерне рішення:
Розширити `build_witness` підтримкою гнучкого пошуку варіантів за regex або лексичним списком:
```python
def find_term_occurrences(data: bytes, term: str, variants: list[str] = None) -> list[int]:
    """Знаходить усі байти початку терміна з урахуванням капіталізації та форм."""
    import re
    search_words = [term] + (variants or [])
    escaped = [re.escape(w.encode('utf-8')) for w in search_words]
    pattern = rb'\b(?:' + rb'|'.join(escaped) + rb')\b'
    return [m.start() for m in re.finditer(pattern, data, flags=re.IGNORECASE)]
```
При цьому свідок фіксує **точні байти** саме тієї форми, яка реально зустрілася у тексті.

---

## Д4. Перенесення слів через дефіс на межі рядків (`time-\nmachine`)

### Проблема:
У друкованих виданнях XIX ст., оцифрованих Project Gutenberg, слова нерідко розбиті дефісом на кінці рядка:
```
time-
machine
```
або
```
heat-
ray
```
Прямий пошук `time machine` чи `heat-ray` не знайде цей випадок, навіть якщо це найраніша поява концепту у творі.

### Інженерне рішення:
У модуль пошуку та сканування (`modules/corpus/scanner.py`) додати нормалізатор пошукового патерна: дефіс і пробіли в багатослівних термінах відповідають регулярному виразу `rb'[-\s]+'`, включаючи переноси рядків `\r?\n\s*`.
Якщо збіг знайдено на переносі рядка, свідок бере повне вікно, що охоплює обидва рядки.

---

## Д5. Автоматизований генератор зон (`modules/corpus/zones.py`) для Т10

### Проблема:
Ручне визначення меж для десятків творів у Т10 (`zones.json`) забирає багато часу і створює ризик людської суб'єктивності при встановленні байтових координат.

### Інженерне рішення:
Створити модуль `modules/corpus/zones.py` із детермінованим авторозмітником на базі структурних маркерів Project Gutenberg:
1. **`front_matter`**: від байта `0` до рядка `*** START OF THE PROJECT GUTENBERG EBOOK ... ***` + преамбула видання до змісту.
2. **`toc` (зміст)**: зона між рядками `CONTENTS`, `TABLE OF CONTENTS` чи `INDEX` та початком розділу (`CHAPTER I`, `BOOK I`, `PART I`).
3. **`body` (основний текст)**: від першого розділу до закінчення роману (`THE END`, `FINIS`, заключні слова автора).
4. **`back_matter`**: післямова автора, колофон, ліцензійні примітки Gutenberg після `*** END OF THE PROJECT GUTENBERG EBOOK ... ***`.

Модуль автоматично генерує `zones.json` поруч із `full_text.md` під час виконання Т3–Т5. Людина може оглянути і підтвердити його.

---

## Д6. Специфікація дериваційної структури для регістру `proposed` (Т8 / Т12)

### Проблема:
У Т8 таблиця `attestations` дозволяє `register = 'proposed'` без CTS URN і без артефакту (`cts_urn IS NULL AND artifact_sha256 IS NULL`). 
Проте ТЗ не визначає чітко, де зберігаються філологічні атрибути української деривації (корінь, афікс, модель), через що вони можуть загубитися або залишитися неструктурованими.

### Інженерне рішення:
Розширити таблицю `attestations` (або зв'язану структуру) чіткими полями для регістру `proposed`:
```sql
ALTER TABLE attestations ADD COLUMN proposed_ukr_term TEXT;
ALTER TABLE attestations ADD COLUMN grinchenko_root TEXT;
ALTER TABLE attestations ADD COLUMN derivation_model TEXT;
ALTER TABLE attestations ADD COLUMN stylistic_note TEXT;
ALTER TABLE attestations ADD COLUMN root_attested_in_grinchenko INTEGER DEFAULT 0;
```
Правило валідації: якщо `register = 'proposed'`, поле `proposed_ukr_term` обов'язково заповнене і проходить морфологічний фільтр Т13.

---

## Д7. Синхронізація ключів `term_id` та `term_orig` (Т8)

### Проблема:
У Т8 наведено схему:
`term_orig TEXT NOT NULL, work_id INTEGER...`
Водночас у документі `docs/COSMOSLOV_WITNESS_ARCHITECTURE_IMPLEMENTATION.md` фігурує:
`term_id INTEGER NOT NULL REFERENCES terms(id)...`

### Інженерне рішення:
Зберегти **обидва поля** в таблиці `attestations`:
```sql
term_id INTEGER REFERENCES terms(id) ON DELETE CASCADE,
term_orig TEXT NOT NULL,
```
- `term_id` гарантує реляційну цілісність із таблицею `terms`.
- `term_orig` забезпечує пряму зручність для аналітичних запитів та створення подання `earliest_attestation` без обов'язкового JOIN.
- Додати індекс: `CREATE INDEX idx_attestations_lookup ON attestations(term_orig, register, zone);`.

---

## Д8. Стандартна функція живого рендерингу цитати `render_quote`

### Проблема:
Оскільки колонка з текстом цитати в базі принципово відсутня (цитата — це виключно координата в запечатаному файлі), для UI, CLI та експорту звітів потрібен уніфікований інтерфейс читання.

### Інженерне рішення:
У `modules/corpus/witness.py` додати офіційну функцію:
```python
def render_quote(witness: dict, file_path: str) -> str:
    """
    Зчитує точні байти свідка з диска і повертає текст.
    Якщо свідок не проходить перевірку цілісності — повертає помилку.
    """
    status, reason, text = verify_witness(witness, file_path, "")
    if status != "ACCEPT":
        return f"[CORRUPTED WITNESS: {reason}]"
    return text.strip()
```
Це забезпечує єдину точку входу для рендерингу в Streamlit Dashboard (`app.py`), CLI та експортері словника.

---

## Підсумок узгодження

| Доповнення | Вплив на ТЗ | Перевага |
| :--- | :--- | :--- |
| **Д1 (CRLF / Git)** | Превентивне налаштування | 100% стабільність SHA-256 та байтових зсувів на Windows |
| **Д2 (UTF-8 Snap)** | Уточнення функції `build_witness` (Т9) | Відсутність випадкових `UnicodeDecodeError` на кирилиці та діакритиці |
| **Д3 (Флексії / Регістр)** | Розширення пошуку (Т9) | Знаходження найперших згадок на початку речень і у множині |
| **Д4 (Дефісні переноси)** | Уточнення пошукового сканера | Знаходження термінів на зламі рядків у XIX столітті |
| **Д5 (Авто-зони)** | Автоматизація Т10 | Швидке та об'єктивне формування `zones.json` |
| **Д6 (Поля proposed)** | Уточнення Т8 / Т12 | Структуроване збереження українських коренів та моделей Грінченка |
| **Д7 (term_id + term_orig)** | Синхронізація схеми Т8 | Реляційна цілісність + швидкість запитів |
| **Д8 (render_quote)** | Допоміжна функція | Прозорий живий рендеринг у консолі та вебі |

Ці доповнення не змінюють жодної суті вимог Т1–Т14, а слугують інженерними запобіжниками для їх бездоганного виконання.
