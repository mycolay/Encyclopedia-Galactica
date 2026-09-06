"""
Rich-based Terminal Command Line Interface for AutoSciFi & Lexicon («Космослов»).
Supports overnight autonomous Karpathy Loop runs, catalog inspection, and lexicographical queries.
"""

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path and UTF-8 is configured
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.db import DatabaseManager
from modules.corpus.manager import CorpusManager
from modules.autoresearch.llm_client import LocalLLMClient
from modules.autoresearch.loop import AutoResearchRunner
from modules.lexicography.dictionary_exporter import DictionaryExporter

app = typer.Typer(help="Автономна система дослідження культової НФ та укладання Словника неологізмів")
console = Console()


@app.command("stats")
def show_stats():
    """Відобразити статистику бази даних та корпусу."""
    db = DatabaseManager()
    stats = db.get_stats()

    table = Table(title="📊 Статистика системи «Космослов»", border_style="blue")
    table.add_column("Метрика", style="cyan", no_wrap=True)
    table.add_column("Значення", style="green bold")

    table.add_row("Авторів у каталозі", str(stats["authors_count"]))
    table.add_row("Культових творів у каталозі", str(stats["works_count"]))
    table.add_row("Повних текстів у корпусі", str(stats["full_texts_count"]))
    table.add_row("Науково-фантастичних термінів", str(stats["terms_count"]))
    table.add_row("Зафіксованих циклів дослідження", str(stats["research_cycles_count"]))

    console.print(table)


@app.command("catalog")
def show_catalog(limit: int = 15):
    """Показати вершину каталогу за рейтингом культовості (Cult Score)."""
    db = DatabaseManager()
    works = db.get_works(limit=limit, order_by="cult_score DESC")

    table = Table(title=f"🏆 Топ-{limit} Культових НФ-творів", border_style="gold1")
    table.add_column("Cult Score", justify="right", style="yellow bold")
    table.add_column("Назва твору", style="white bold")
    table.add_column("Автор", style="cyan")
    table.add_column("Рік", justify="center", style="magenta")
    table.add_column("Текст у корпусі", justify="center")

    for w in works:
        has_text = "✅ Є" if w.get("has_full_text") else "⏳ Очікує"
        score_str = f"{w['cult_score']:.1f}"
        table.add_row(score_str, f"{w['title_ukr']} ({w['title_orig']})", f"{w['author_name_ukr']}", str(w["year"]), has_text)

    console.print(table)


@app.command("dictionary")
def show_dictionary(search: str = ""):
    """Показати статті академічного словника науково-фантастичних неологізмів."""
    db = DatabaseManager()
    terms = db.get_terms(limit=20, search=search if search else None)

    if not terms:
        console.print("[yellow]Термінів за запитом не знайдено.[/yellow]")
        return

    for t in terms:
        neologisms_text = "\n".join([
            f"  • [bold green]{n.get('variant')}[/bold green]: {n.get('morphemes')} ({n.get('grinchenko_model')})"
            for n in t.get("ukr_grinchenko_neologisms", [])
        ])

        panel_content = (
            f"[bold]Автор:[/bold] {t.get('author_name_ukr')} | [bold]Твір:[/bold] «{t.get('work_title_ukr')}» ({t.get('first_attestation_year')})\n"
            f"[bold]Категорія:[/bold] {t.get('concept_category')}\n"
            f"[bold]Наукова дефініція:[/bold] {t.get('scientific_definition')}\n\n"
            f"[italic cyan]Оригінальний контекст:[/italic cyan]\n«{t.get('original_context')}»\n\n"
            f"[bold yellow]Українські варіанти за Грінченком:[/bold yellow]\n{neologisms_text}\n\n"
            f"[bold]Приклад перекладу в контексті:[/bold]\n«{t.get('ukr_translated_context')}»"
        )
        console.print(Panel(panel_content, title=f"❖ {t['term_orig'].upper()} {t.get('ipa') or ''}", border_style="blue"))


@app.command("run-cycle")
def run_cycle(model: str = "qwen3.5:27b"):
    """Запустити 1 цикл Karpathy Loop з використанням локальної моделі на RTX 3090."""
    db = DatabaseManager()
    corpus_mgr = CorpusManager()
    llm_client = LocalLLMClient(model_name=model)

    if not llm_client.is_available():
        console.print("[red]Помилка: сервіс Ollama недоступний на http://localhost:11434[/red]")
        raise typer.Exit(code=1)

    runner = AutoResearchRunner(db=db, corpus_mgr=corpus_mgr, llm_client=llm_client)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Виконується цикл дослідження на {model} (RTX 3090)...", total=None)
        res = runner.run_single_cycle()

    if res.get("status") == "committed":
        console.print(f"[bold green]✅ УСПІХ! Зафіксовано термін:[/bold green] [yellow]{res.get('term')}[/yellow]")
        console.print(f"   Твір: {res.get('work')} | Оцінка якості: {res.get('score')}")
    elif res.get("status") == "rolled_back":
        console.print(f"[bold yellow]⚠️ ВІДХИЛЕНО КРИТИКОМ (Rollback):[/bold yellow] Термін: {res.get('term')}, Оцінка: {res.get('score')}")
    else:
        console.print(f"[red]Помилка або завершення черги:[/red] {res}")


@app.command("export")
def export_docs():
    """Оновити та експортувати академічний Словник у docs/SCI_FI_LEXICON.md."""
    db = DatabaseManager()
    exporter = DictionaryExporter(db)
    path = exporter.export_markdown()
    console.print(f"[green]Академічний словник успішно оновлено:[/green] [cyan]{path}[/cyan]")


if __name__ == "__main__":
    app()
