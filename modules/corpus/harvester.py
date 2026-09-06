"""
Public-Domain Sci-Fi Harvester for NAS Library.
Downloads unabridged canonical masterworks from Project Gutenberg & Standard Ebooks,
strips boilerplate, and compiles them into the LLM-Ready format on K:\\scifi_library.
"""

import re
import logging
import requests
from typing import List, Dict, Any, Optional, Callable
from modules.corpus.manager import CorpusManager
from core.db import DatabaseManager

logger = logging.getLogger("AutoSciFi.Harvester")

PUBLIC_DOMAIN_SF_MASTERS = [
    {
        "slug": "frankenstein",
        "title_orig": "Frankenstein; or, The Modern Prometheus",
        "title_ukr": "Франкенштайн, або Сучасний Прометей",
        "author_slug": "mary-shelley",
        "author_name_orig": "Mary Shelley",
        "author_name_ukr": "Мері Шеллі",
        "year": 1818,
        "original_lang": "en",
        "gutenberg_id": 84,
        "subgenres": ["Gothic Sci-Fi", "Artificial Life", "Proto-SF"],
        "awards": ["Foundational First Sci-Fi Novel", "All-Time World Masterpiece"],
        "trope_maker": True,
        "synopsis": "Основоположний перший роман наукової фантастики. Вчений Віктор Франкенштайн осягає таємницю життя та створює живу розумну істоту з мертвої матерії за допомогою гальванізму й хімії."
    },
    {
        "slug": "the-time-machine",
        "title_orig": "The Time Machine",
        "title_ukr": "Машина часу",
        "author_slug": "h-g-wells",
        "author_name_orig": "H.G. Wells",
        "author_name_ukr": "Герберт Веллс",
        "year": 1895,
        "original_lang": "en",
        "gutenberg_id": 35,
        "subgenres": ["Time Travel", "Dying Earth", "Evolutionary SF"],
        "awards": ["Trope Maker: Time Travel Vehicle", "SF Masterworks"],
        "trope_maker": True,
        "synopsis": "Твір, який ввів у світову культуру концепцію та термін 'машина часу'. Мандрівник у часі вирушає у 802 701 рік, де людство розкололося на вироджених безтурботних елоїв та підземних канібалів-морлоків."
    },
    {
        "slug": "the-war-of-the-worlds",
        "title_orig": "The War of the Worlds",
        "title_ukr": "Війна світів",
        "author_slug": "h-g-wells",
        "author_name_orig": "H.G. Wells",
        "author_name_ukr": "Герберт Веллс",
        "year": 1898,
        "original_lang": "en",
        "gutenberg_id": 36,
        "subgenres": ["Alien Invasion", "Hard SF", "Planetary War"],
        "awards": ["First Alien Invasion Novel", "SF Masterworks"],
        "trope_maker": True,
        "synopsis": "Марсіяни атакують Землю за допомогою бойових триног, теплових променів та отруйного чорного диму. Канонічна історія першого міжпланетного вторгнення."
    },
    {
        "slug": "the-invisible-man",
        "title_orig": "The Invisible Man",
        "title_ukr": "Невидимець",
        "author_slug": "h-g-wells",
        "author_name_orig": "H.G. Wells",
        "author_name_ukr": "Герберт Веллс",
        "year": 1897,
        "original_lang": "en",
        "gutenberg_id": 5230,
        "subgenres": ["Optics Sci-Fi", "Mad Scientist", "Proto-SF"],
        "awards": ["All-Time Canon Induction"],
        "trope_maker": True,
        "synopsis": "Вчений Гріффін відкриває спосіб змінювати показник заломлення світла людського тіла, роблячи його абсолютно невидимим, проте експеримент руйнує його психіку."
    },
    {
        "slug": "the-island-of-doctor-moreau",
        "title_orig": "The Island of Doctor Moreau",
        "title_ukr": "Острів доктора Моро",
        "author_slug": "h-g-wells",
        "author_name_orig": "H.G. Wells",
        "author_name_ukr": "Герберт Веллс",
        "year": 1896,
        "original_lang": "en",
        "gutenberg_id": 159,
        "subgenres": ["Biological SF", "Uplift", "Philosophical SF"],
        "awards": ["Trope Maker: Animal Uplift"],
        "trope_maker": True,
        "synopsis": "Доктор Моро на віддаленому острові хірургічно та генетично перетворює звірів на подобу людей, досліджуючи межі людяності та тваринної природи."
    },
    {
        "slug": "twenty-thousand-leagues-under-the-sea",
        "title_orig": "Twenty Thousand Leagues Under the Sea",
        "title_ukr": "Двадцять тисяч льє під водою",
        "author_slug": "jules-verne",
        "author_name_orig": "Jules Verne",
        "author_name_ukr": "Жуль Верн",
        "year": 1870,
        "original_lang": "fr",
        "gutenberg_id": 164,
        "subgenres": ["Underwater Sci-Fi", "Techno-Thriller", "Hard SF"],
        "awards": ["All-Time World Masterpiece", "Porges Century Canon"],
        "trope_maker": True,
        "synopsis": "Професор Аронакс потрапляє на борт підводного човна 'Наутілус' під командуванням загадкового капітана Немо, здійснюючи навколосвітню наукову експедицію глибинами океану."
    },
    {
        "slug": "from-the-earth-to-the-moon",
        "title_orig": "From the Earth to the Moon",
        "title_ukr": "З Землі на Місяць",
        "author_slug": "jules-verne",
        "author_name_orig": "Jules Verne",
        "author_name_ukr": "Жуль Верн",
        "year": 1865,
        "original_lang": "fr",
        "gutenberg_id": 83,
        "subgenres": ["Space Travel", "Hard SF", "Ballistics"],
        "awards": ["First Scientific Spaceflight Novel"],
        "trope_maker": True,
        "synopsis": "Балтиморський Гарматний клуб споруджує колосальну колумбіаду у Флориді, щоб запустити алюмінієвий снаряд із трьома дослідниками до Місяця. Верн вражаюче точно передбачив координати старту майбутнього Аполлона."
    },
    {
        "slug": "journey-to-the-center-of-the-earth",
        "title_orig": "A Journey to the Centre of the Earth",
        "title_ukr": "Подорож до центру Землі",
        "author_slug": "jules-verne",
        "author_name_orig": "Jules Verne",
        "author_name_ukr": "Жуль Верн",
        "year": 1864,
        "original_lang": "fr",
        "gutenberg_id": 18857,
        "subgenres": ["Subterranean SF", "Geological SF", "Adventure"],
        "awards": ["All-Time Canon Induction"],
        "trope_maker": True,
        "synopsis": "Професор Лідонброк знаходить стародавній шифр і разом з племінником спускається в кратер згаслого ісландського вулкана Снайфедльс, потрапляючи у доісторичний підземний світ."
    },
    {
        "slug": "flatland",
        "title_orig": "Flatland: A Romance of Many Dimensions",
        "title_ukr": "Флетландія: Роман у багатьох вимірах",
        "author_slug": "edwin-a-abbott",
        "author_name_orig": "Edwin A. Abbott",
        "author_name_ukr": "Едвін А. Ебботт",
        "year": 1884,
        "original_lang": "en",
        "gutenberg_id": 97,
        "subgenres": ["Mathematical SF", "Dimensionality", "Satire"],
        "awards": ["Trope Maker: Higher Dimensions / 4D Space"],
        "trope_maker": True,
        "synopsis": "Математичний шедевр про мешканця двовимірного світу (Квадрата), якого відвідує тривимірна Сфера. Книга розкриває геометрію простору вищих вимірів і поняття тесеракта."
    },
    {
        "slug": "a-princess-of-mars",
        "title_orig": "A Princess of Mars",
        "title_ukr": "Принцеса Марса",
        "author_slug": "edgar-rice-burroughs",
        "author_name_orig": "Edgar Rice Burroughs",
        "author_name_ukr": "Едгар Райс Берроуз",
        "year": 1912,
        "original_lang": "en",
        "gutenberg_id": 62,
        "subgenres": ["Planetary Romance", "Space Fantasy", "Pulp SF"],
        "awards": ["Trope Maker: Planetary Romance / Barsoom"],
        "trope_maker": True,
        "synopsis": "Джон Картер містичним чином переноситься на вмираючий Марс (Барсум) з низькою гравітацією, чотирирукими тарками, летючими кораблями та прекрасною Деєю Торіс."
    }
]


class PublicDomainHarvester:
    def __init__(self, corpus_mgr: CorpusManager, db: DatabaseManager):
        self.corpus_mgr = corpus_mgr
        self.db = db

    def clean_gutenberg_text(self, text: str) -> str:
        """Removes Gutenberg boilerplate headers and footers."""
        header_patterns = [
            r"\*\*\*\s*START OF TH(?:E|IS) PROJECT GUTENBERG EBOOK[^\*]*\*\*\*",
            r"\*\*\*\s*START OF THE PROJECT GUTENBERG[^\*]*\*\*\*"
        ]
        footer_patterns = [
            r"\*\*\*\s*END OF TH(?:E|IS) PROJECT GUTENBERG EBOOK",
            r"\*\*\*\s*END OF THE PROJECT GUTENBERG"
        ]

        cleaned = text
        for hp in header_patterns:
            parts = re.split(hp, cleaned, flags=re.IGNORECASE)
            if len(parts) > 1:
                cleaned = parts[-1]
                break

        for fp in footer_patterns:
            parts = re.split(fp, cleaned, flags=re.IGNORECASE)
            if len(parts) > 1:
                cleaned = parts[0]
                break

        return cleaned.strip()

    def fetch_from_gutenberg(self, gutenberg_id: int) -> Optional[str]:
        """Fetches raw text by Gutenberg ID using multiple reliable mirrors."""
        urls = [
            f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
            f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
            f"https://raw.githubusercontent.com/the-best-book/gutenberg-mirror/main/{gutenberg_id}.txt"
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutoSciFi-Harvester/2.0"
        }

        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    return resp.text
            except Exception as e:
                logger.debug(f"Mirror failed {url}: {e}")
                continue
        return None

    def harvest_work(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Downloads, cleans, and packages a work directly into NAS K:\\scifi_library."""
        g_id = spec.get("gutenberg_id")
        if not g_id:
            return {"status": "error", "message": "No gutenberg_id provided"}

        logger.info(f"Завантаження з Gutenberg (ID {g_id}): {spec['title_orig']}")
        raw_text = self.fetch_from_gutenberg(g_id)
        if not raw_text:
            return {"status": "error", "message": f"Could not download text for Gutenberg ID {g_id}"}

        clean_text = self.clean_gutenberg_text(raw_text)

        # 1. Package into NAS format
        pkg_res = self.corpus_mgr.package_llm_ready_work(
            author_slug=spec["author_slug"],
            work_slug=spec["slug"],
            text=clean_text,
            metadata={
                "title": spec["title_orig"],
                "title_ukr": spec["title_ukr"],
                "author_name": spec["author_name_orig"],
                "author_ukr": spec["author_name_ukr"],
                "year": spec["year"],
                "original_lang": spec["original_lang"],
                "subgenres": spec.get("subgenres", []),
                "synopsis": spec.get("synopsis", "")
            }
        )

        # 2. Ensure author exists in DB
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM authors WHERE slug = ?", (spec["author_slug"],))
            row = cursor.fetchone()
            if not row:
                cursor = conn.execute("""
                INSERT INTO authors (slug, name_orig, name_ukr, country, primary_language, cult_tier, cult_score)
                VALUES (?, ?, ?, ?, ?, 1, 95.0) RETURNING id;
                """, (spec["author_slug"], spec["author_name_orig"], spec["author_name_ukr"], "International", spec["original_lang"]))
                author_id = cursor.fetchone()[0]
            else:
                author_id = row[0]

            # 3. Update or Insert Work in DB
            conn.execute("""
            INSERT INTO works (slug, author_id, title_orig, title_ukr, year, original_lang,
                              form, subgenres_json, awards_json, cult_score, synopsis,
                              has_full_text, text_path, word_count, research_status)
            VALUES (?, ?, ?, ?, ?, ?, 'Novel', '[]', '[]', 96.0, ?, 1, ?, ?, 'pending')
            ON CONFLICT(slug) DO UPDATE SET
                has_full_text = 1,
                text_path = excluded.text_path,
                word_count = excluded.word_count,
                synopsis = excluded.synopsis;
            """, (
                spec["slug"], author_id, spec["title_orig"], spec["title_ukr"],
                spec["year"], spec["original_lang"], spec.get("synopsis", ""),
                pkg_res["full_text_path"], pkg_res["word_count"]
            ))
            conn.commit()

        return {
            "status": "success",
            "title": spec["title_orig"],
            "word_count": pkg_res["word_count"],
            "chapters_count": pkg_res["chapters_count"],
            "full_text_path": pkg_res["full_text_path"],
            "is_nas": pkg_res["is_nas"]
        }

    def harvest_all_public_domain(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """Batch harvests the full public-domain sci-fi masterpieces collection."""
        results = []
        for spec in PUBLIC_DOMAIN_SF_MASTERS:
            res = self.harvest_work(spec)
            results.append(res)
            if callback:
                callback(res)
        return results
