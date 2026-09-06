"""
Streamlit Web Dashboard for AutoSciFi & Lexicon («Космослов»).
Features:
- Cult SF Catalog (1000+ ranked works & authors)
- Academic Sci-Fi Neologisms Lexicon (Grinchenko-inspired morphology)
- Original-Language Text Corpus Reader
- AutoResearch Control Deck (The Karpathy Loop on RTX 3090)
"""

import sys
import os
import subprocess
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import streamlit as st
import pandas as pd
from core.db import DatabaseManager
from modules.corpus.manager import CorpusManager
from modules.autoresearch.llm_client import LocalLLMClient
from modules.autoresearch.loop import AutoResearchRunner
from modules.lexicography.grinchenko_engine import GRINCHENKO_PREFIXES, GRINCHENKO_SUFFIXES

# Set page configuration
st.set_page_config(
    page_title="Космослов — Культовий НФ-Каталог & Словник",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .cult-badge {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .term-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .quote-box {
        background: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 10px 14px;
        margin: 10px 0;
        font-style: italic;
        border-radius: 0 6px 6px 0;
    }
    .grinchenko-box {
        background: #ECFDF5;
        border-left: 4px solid #10B981;
        padding: 12px 14px;
        margin: 10px 0;
        border-radius: 0 6px 6px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db():
    return DatabaseManager()


@st.cache_resource
def get_corpus():
    return CorpusManager()


def get_gpu_info():
    """Queries nvidia-smi for current RTX 3090 status."""
    try:
        cmd = "nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu --format=csv,noheader,nounits"
        out = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        parts = [p.strip() for p in out.split(",")]
        return {
            "name": parts[0],
            "mem_used": int(parts[1]),
            "mem_total": int(parts[2]),
            "temp": int(parts[3]),
            "util": int(parts[4])
        }
    except Exception:
        return None


db = get_db()
corpus_mgr = get_corpus()
stats = db.get_stats()

# Header
st.markdown("<div class='main-title'>🌌 «КОСМОСЛОВ» — Супер-Каталог & Словник НФ</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Академічний індекс культової наукової фантастики, корпус оригіналів та Словник авторських неологізмів за моделями Бориса Грінченка</div>",
    unsafe_allow_html=True
)

# Sidebar
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=400", use_container_width=True)
    st.markdown("### 📊 Статистика системи")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Авторів", stats["authors_count"])
    col_s2.metric("Творів", stats["works_count"])
    col_s3, col_s4 = st.columns(2)
    col_s3.metric("Текстів", stats["full_texts_count"])
    col_s4.metric("Термінів", stats["terms_count"])

    st.markdown("---")
    st.markdown("### 🖥️ Апаратний вузол (GPU)")
    gpu = get_gpu_info()
    if gpu:
        st.write(f"**GPU**: `{gpu['name']}`")
        mem_pct = round((gpu['mem_used'] / gpu['mem_total']) * 100, 1)
        st.progress(mem_pct / 100.0)
        st.caption(f"VRAM: **{gpu['mem_used']} MiB** / {gpu['mem_total']} MiB ({mem_pct}%) | Темп: **{gpu['temp']}°C**")
    else:
        st.info("NVIDIA GPU: інформація недоступна або драйвер зайнятий.")

    st.markdown("---")
    st.caption("Система функціонує за архітектурою **AutoResearch (The Karpathy Loop)**.")

# Main Navigation Tabs
tab_catalog, tab_lexicon, tab_corpus, tab_autoresearch, tab_grinchenko = st.tabs([
    "🏆 Культовий Каталог (Top-1000)",
    "📖 Словник неологізмів («Космослов»)",
    "📚 Корпус текстів оригіналу",
    "⚡ AutoResearch Deck (Karpathy Loop)",
    "🧬 Моделі словотвору Грінченка"
])

# ----------------------------------------------------------------------
# TAB 1: CULT SF CATALOG
# ----------------------------------------------------------------------
with tab_catalog:
    st.subheader("Рейтинг культовості НФ-творів та авторів")
    st.markdown(
        "Ранжування здійснюється за композитною формулою **Cult Index**, що враховує перемоги й номінації на премії "
        "(Hugo, Nebula, Locus, Clarke, BSFA, Campbell, Philip K. Dick), канонічні антології (SF Masterworks, NPR Top 100) та статус винахідника парадигми (Trope Maker)."
    )

    c1, c2, c3 = st.columns([2, 1, 1])
    search_q = c1.text_input("🔍 Пошук за назвою або автором:", "")
    min_score = c2.slider("Мінімальний Cult Score:", 50.0, 100.0, 50.0, 1.0)
    has_text_filter = c3.selectbox("Наявність тексту:", ["Всі", "Лише з текстом у корпусі"])

    works = db.get_works(limit=200, order_by="cult_score DESC")
    filtered_works = []
    for w in works:
        if w["cult_score"] < min_score:
            continue
        if has_text_filter == "Лише з текстом у корпусі" and not w.get("has_full_text"):
            continue
        if search_q:
            sq = search_q.lower()
            in_title = sq in w["title_orig"].lower() or sq in w["title_ukr"].lower()
            in_author = sq in w["author_name_orig"].lower() or sq in w["author_name_ukr"].lower()
            if not (in_title or in_author):
                continue
        filtered_works.append(w)

    df_data = []
    for i, w in enumerate(filtered_works, 1):
        df_data.append({
            "№": i,
            "Cult Score": f"{w['cult_score']:.1f}",
            "Назва українською": w["title_ukr"],
            "Оригінальна назва": w["title_orig"],
            "Автор": f"{w['author_name_ukr']} ({w['author_name_orig']})",
            "Рік": w["year"],
            "Форма": w["form"],
            "Текст": "✅ Є" if w.get("has_full_text") else "⏳ Очікує",
            "Дослідження": "🟢 Завершено" if w.get("research_status") == "analyzed" else "⚪ В черзі"
        })

    if df_data:
        st.dataframe(pd.DataFrame(df_data), use_container_width=True, height=400)
    else:
        st.info("Творів за вказаними фільтрами не знайдено.")

    # Detailed Work Card
    st.markdown("### 🔎 Картка твору")
    selected_slug = st.selectbox(
        "Оберіть твір для детального перегляду:",
        [w["slug"] for w in filtered_works],
        format_func=lambda s: next((f"{w['title_ukr']} ({w['title_orig']}, {w['year']}) — {w['author_name_ukr']}" for w in filtered_works if w['slug'] == s), s)
    )

    if selected_slug:
        w_detail = next(w for w in filtered_works if w["slug"] == selected_slug)
        col_w1, col_w2 = st.columns([3, 1])
        with col_w1:
            st.markdown(f"#### {w_detail['title_ukr']} / *{w_detail['title_orig']}* ({w_detail['year']})")
            st.markdown(f"**Автор**: {w_detail['author_name_ukr']} (*{w_detail['author_name_orig']}*)")
            st.markdown(f"**Піджанри**: {', '.join(w_detail.get('subgenres', []))}")
            st.markdown(f"**Синопсис**: {w_detail.get('synopsis', 'Опис відсутній.')}")
        with col_w2:
            st.metric("Cult Score", f"{w_detail['cult_score']:.1f} / 100")
            st.markdown(f"**Нагороди**: {', '.join(w_detail.get('awards', [])) or '—'}")
            st.markdown(f"**Канони**: {', '.join(w_detail.get('canon_inclusions', [])) or '—'}")


# ----------------------------------------------------------------------
# TAB 2: SCI-FI LEXICON (GRINCHENKO MODEL)
# ----------------------------------------------------------------------
with tab_lexicon:
    st.subheader("Академічний Словник науково-фантастичних неологізмів («Космослов»)")
    st.markdown(
        "Кожна стаття містить наукову дефініцію, точну цитату мовою оригіналу з моменту першої фіксації слова, "
        "та творчу українську деривацію, що базується на глибинних морфологічних законах «Словаря української мови» Б. Грінченка."
    )

    col_l1, col_l2 = st.columns([2, 1])
    lex_search = col_l1.text_input("🔍 Повнотекстовий пошук за гаслом, визначенням чи перекладом:", "")
    categories = ["Всі категорії", "Штучний інтелект та кібернетика", "Віртуальна реальність та кібернетика",
                  "Надсвітловий зв'язок та релятивістська фізика", "Математична соціологія та прогнозування",
                  "Когнітивні розширення та людські комп'ютери"]
    sel_cat = col_l2.selectbox("Категорія:", categories)

    cat_filter = None if sel_cat == "Всі категорії" else sel_cat
    terms = db.get_terms(limit=200, category=cat_filter, search=lex_search if lex_search else None)

    st.write(f"Знайдено термінів: **{len(terms)}**")

    for t in terms:
        with st.container():
            st.markdown(f"""
            <div class='term-card'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h3 style='margin: 0; color: #1E3A8A;'>❖ {t['term_orig'].upper()} <span style='font-size: 1rem; color: #6B7280;'>{t.get('ipa') or ''}</span></h3>
                    <span class='cult-badge'>Оцінка якості: {t.get('verification_score', 0.0):.2f}</span>
                </div>
                <p style='color: #4B5563; margin-top: 4px;'>
                    <b>Авторство:</b> {t.get('author_name_ukr')} ({t.get('author_name_orig')}) | 
                    <b>Твір:</b> «{t.get('work_title_ukr')}» (<i>{t.get('work_title_orig')}</i>), <b>{t.get('first_attestation_year')} рік</b> |
                    <b>Категорія:</b> {t.get('concept_category')}
                </p>
                <p><b>Наукова дефініція:</b> {t.get('scientific_definition')}</p>
                <div class='quote-box'>
                    <b>Цитата першої появи (мовою оригіналу):</b><br>
                    «{t.get('original_context')}»
                </div>
                <p><b>Існуючий традиційний переклад:</b> <i>{t.get('ukr_traditional') or '—'}</i></p>
                <div class='grinchenko-box'>
                    <h4 style='margin-top: 0; color: #065F46;'>🌱 Творча інтерпретація за моделями словника Грінченка:</h4>
            """, unsafe_allow_html=True)

            neologisms = t.get("ukr_grinchenko_neologisms", [])
            for n in neologisms:
                st.markdown(f"- **{n.get('variant')}** — *{n.get('morphemes')}* (Модель: *{n.get('grinchenko_model')}*). {n.get('semantic_nuance')}")

            st.markdown(f"""
                    <p style='margin-top: 10px;'><b>Академічне обґрунтування:</b> {t.get('morphological_rationale')}</p>
                </div>
                <div style='background: #F3F4F6; padding: 10px; border-radius: 6px; font-size: 0.95rem;'>
                    <b>Художній приклад в українському перекладі:</b><br>
                    «{t.get('ukr_translated_context')}»
                </div>
            </div>
            """, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# TAB 3: TEXT CORPUS READER
# ----------------------------------------------------------------------
with tab_corpus:
    st.subheader("Корпус текстів оригіналу (Original Language Texts)")
    st.markdown("Сховище повних текстів та канонічних фрагментів мовами першодруку для верифікації перших згадок термінів.")

    corpus_works = [w for w in db.get_works(limit=100) if w.get("has_full_text")]
    if corpus_works:
        sel_corpus_work = st.selectbox(
            "Оберіть твір з корпусу для читання:",
            corpus_works,
            format_func=lambda w: f"{w['title_orig']} — {w['author_name_orig']} ({w['year']}) [{w.get('word_count', 0)} слів]"
        )

        if sel_corpus_work:
            text_content = None
            if sel_corpus_work.get("text_path") and Path(sel_corpus_work["text_path"]).exists():
                with open(sel_corpus_work["text_path"], "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()

            if text_content:
                st.caption(f"Файл: `{sel_corpus_work.get('text_path')}` | Мова: `{sel_corpus_work.get('original_lang')}`")
                highlight_term = st.text_input("🔍 Підсвітити або знайти термін у тексті:", "")

                if highlight_term:
                    contexts = corpus_mgr.search_term_context(text_content, highlight_term)
                    if contexts:
                        st.success(f"Знайдено збігів: {len(contexts)}")
                        for c in contexts:
                            st.markdown(f"> ...{c['context']}...")
                    else:
                        st.warning(f"Термін '{highlight_term}' не знайдено у тексті.")

                st.text_area("Повний текст мовою оригіналу:", text_content, height=450)
            else:
                st.error("Файл тексту не знайдено на диску.")
    else:
        st.info("У корпусі наразі немає завантажених текстів. Виконайте ініціалізацію або завантаження.")


# ----------------------------------------------------------------------
# TAB 4: AUTORESEARCH DECK (KARPATHY LOOP)
# ----------------------------------------------------------------------
with tab_autoresearch:
    st.subheader("⚡ Пульт управління AutoResearch (The Karpathy Loop)")
    st.markdown(
        "Автономний дослідник Андрія Карпатого реалізує безперервний цикл: "
        "**Propose** (висування гіпотези) ➔ **Execute** (локальна LLM на RTX 3090) ➔ **Synthesize** (деривація за Грінченком) "
        "➔ **Evaluate** (скоринг та критик) ➔ **Commit / Rollback**."
    )

    llm_models = ["qwen3.5:27b", "qwen3.6:35b", "gemma3:27b", "gpt-4o:latest"]
    col_a1, col_a2 = st.columns(2)
    selected_model = col_a1.selectbox("Локальна LLM (Ollama на RTX 3090):", llm_models, index=0)

    pending_works = [w for w in db.get_works(limit=50) if w.get("has_full_text") and w.get("research_status") != "analyzed"]
    target_options = ["Автоматичний вибір з черги (Auto-Queue)"] + [f"{w['title_orig']} ({w['author_name_orig']})" for w in pending_works]
    selected_target_str = col_a2.selectbox("Цільовий твір для циклу:", target_options)

    llm_client = LocalLLMClient(model_name=selected_model)
    runner = AutoResearchRunner(db=db, corpus_mgr=corpus_mgr, llm_client=llm_client)

    col_btn1, col_btn2 = st.columns([1, 4])
    start_cycle_btn = col_btn1.button("🚀 Запустити 1 цикл Karpathy Loop", type="primary")

    if start_cycle_btn:
        target_work = None
        if selected_target_str != "Автоматичний вибір з черги (Auto-Queue)":
            chosen_title = selected_target_str.split(" (")[0]
            target_work = next((w for w in pending_works if w["title_orig"] == chosen_title), None)

        with st.spinner(f"Виконується цикл Karpathy Loop на моделі {selected_model} (RTX 3090)..."):
            try:
                res = runner.run_single_cycle(target_work)
                if res.get("status") == "committed":
                    st.success(f"✅ Успішно зафіксовано! Термін: **{res.get('term')}** для твору *{res.get('work')}*. Оцінка якості: **{res.get('score')}**")
                    st.json(res.get("eval_details"))
                elif res.get("status") == "rolled_back":
                    st.warning(f"⚠️ Відхилено критиком (Rollback). Термін: {res.get('term')}. Оцінка: {res.get('score')}")
                    st.json(res.get("eval_details"))
                else:
                    st.info(f"Статус: {res}")
            except Exception as e:
                st.error(f"Помилка виконання циклу: {e}")

    st.markdown("---")
    st.markdown("### 📜 Журнал дослідницьких циклів (Research Cycles Log)")
    cycles = db.get_cycles(limit=20)
    if cycles:
        cycle_df = pd.DataFrame(cycles)
        st.dataframe(
            cycle_df[["id", "timestamp", "target_work_title", "status", "loss_or_quality_score", "llm_model", "notes"]],
            use_container_width=True
        )
    else:
        st.info("Жодного циклу автодослідника ще не зафіксовано.")


# ----------------------------------------------------------------------
# TAB 5: GRINCHENKO MORPHOLOGY EXPLORER
# ----------------------------------------------------------------------
with tab_grinchenko:
    st.subheader("🧬 Морфологічний компас Словника Бориса Грінченка")
    st.markdown(
        "Інвентар питомих українських префіксів та суфіксів, які використовує агент для конструювання науково-фантастичних термінів "
        "замість сліпого копіювання іноземних слів."
    )

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### Автентичні префікси просторово-часової градації")
        for pref, desc in GRINCHENKO_PREFIXES.items():
            st.markdown(f"- **`{pref}`** — {desc}")

    with col_g2:
        st.markdown("#### Продуктивні суфікси апаратотворення та опредметнення")
        for suf, desc in GRINCHENKO_SUFFIXES.items():
            st.markdown(f"- **`{suf}`** — {desc}")
