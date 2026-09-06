"""
Canonical Seed Dataset of Cult Science Fiction Authors and Works.
Spans Proto-SF, Golden Age, New Wave, Cyberpunk, Hard SF, and Modern Eras.
"""

from typing import List, Dict, Any
from core.models import Author, Work
from modules.catalog.ranker import CultRanker

AUTHORS_SEED: List[Dict[str, Any]] = [
    {
        "slug": "karel-capek",
        "name_orig": "Karel Čapek",
        "name_ukr": "Карел Чапек",
        "birth_year": 1890,
        "death_year": 1938,
        "country": "Czech Republic",
        "primary_language": "cs",
        "cult_tier": 1,
        "awards_summary": "7-time Nobel Prize in Literature Nominee",
        "trope_influence": "Винахідник слова 'робот' (robot); засновник філософсько-антропологічної драми про штучне життя",
        "bio_summary": "Видатний чеський письменник, драматург, інтелектуал. Спільно з братом Йозефом Чапеком у п'єсі 'R.U.R.' (1920) подарував світовій культурі термін 'робот' від чеського 'robota' (панщина, тяжка примусова праця)."
    },
    {
        "slug": "william-gibson",
        "name_orig": "William Gibson",
        "name_ukr": "Вільям Ґібсон",
        "birth_year": 1948,
        "death_year": None,
        "country": "USA / Canada",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "Hugo, Nebula, Philip K. Dick, Seiun Award Winner (Triple Crown of SF)",
        "trope_influence": "Хрещений батько кіберпанку; винахідник концептів 'кіберпростір' (cyberspace), 'матриця', 'simstim', 'ICE'",
        "bio_summary": "Американсько-канадський письменник, який радикально змінив наукову фантастику 1980-х романом 'Neuromancer'. Передбачив інтернет, кіберкультуру, глобальну владу мегакорпорацій та злиття людини з мережею."
    },
    {
        "slug": "ursula-k-le-guin",
        "name_orig": "Ursula K. Le Guin",
        "name_ukr": "Урсула К. Ле Ґуїн",
        "birth_year": 1929,
        "death_year": 2018,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "6 Hugo, 6 Nebula, 24 Locus, Grand Master of SF (Damon Knight Memorial)",
        "trope_influence": "Творець терміна 'ansible' (надсвітловий зв'язок); піонерка антропологічної, гендерної та анархістської НФ (Гайнський цикл)",
        "bio_summary": "Одна з найвпливовіших авторок світової літератури XX століття. Поєднала наукову строгість культурної антропології з глибокою даоською філософією у шедеврах 'The Left Hand of Darkness' та 'The Dispossessed'."
    },
    {
        "slug": "frank-herbert",
        "name_orig": "Frank Herbert",
        "name_ukr": "Френк Герберт",
        "birth_year": 1920,
        "death_year": 1986,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "Hugo, Nebula Winner; найпродаваніший НФ-роман в історії",
        "trope_influence": "Творець екологічної космоопери; поняття 'Батлеріанський джихад', гільдійські навігатори, спайс, ментати",
        "bio_summary": "Автор монументального циклу 'Хроніки Дюни'. Створив найдетальніший у світовій фантастиці симбіоз екології пустелі, релігійного месіанізму, геополітики та надлюдської свідомості."
    },
    {
        "slug": "stanislaw-lem",
        "name_orig": "Stanisław Lem",
        "name_ukr": "Станіслав Лем",
        "birth_year": 1921,
        "death_year": 2006,
        "country": "Poland",
        "primary_language": "pl",
        "cult_tier": 1,
        "awards_summary": "Орден Білого Орла, премія Франца Кафки, всесвітній філософський канон",
        "trope_influence": "Концепція принципової непізнаваності позаземного розуму (Соляріс); нанороботична мікроеволюція ('Непереможний'); автоеволюція розуму",
        "bio_summary": "Польський мислитель, футуролог і сатирик, народжений у Львові. Його твори ('Соляріс', 'Голос Неба', 'Непереможний', 'Кіберіада') є вершиною філософського дослідження контакту та технологічної сингулярності."
    },
    {
        "slug": "isaac-asimov",
        "name_orig": "Isaac Asimov",
        "name_ukr": "Айзек Азімов",
        "birth_year": 1920,
        "death_year": 1992,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "Special Hugo for Best All-Time Series (Foundation), 5 Hugo, 3 Nebula, Grand Master",
        "trope_influence": "Три закони робототехніки, позитронний мозок, психоісторія (psychohistory), галактична імперія",
        "bio_summary": "Один із 'Великої трійки' золотої доби фантастики. Професор біохімії, який сформував сучасне розуміння штучного інтелекту, етики роботів та математичного моделювання соціуму."
    },
    {
        "slug": "arthur-c-clarke",
        "name_orig": "Arthur C. Clarke",
        "name_ukr": "Артур К. Кларк",
        "birth_year": 1917,
        "death_year": 2008,
        "country": "UK",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "Hugo, Nebula, Campbell, Рыцарский титул сэр, Grand Master",
        "trope_influence": "Космічний ліфт, геостаціонарні супутники зв'язку (орбіта Кларка), моноліти предтеч, концепт 'надрозуму'",
        "bio_summary": "Британський учений, винахідник і візіонер. Співавтор фільму Стенлі Кубрика '2001: Космічна одіссея'. Сформулював знаменитий закон: 'Будь-яка достатньо розвинена технологія не відрізняється від магії'."
    },
    {
        "slug": "philip-k-dick",
        "name_orig": "Philip K. Dick",
        "name_ukr": "Філіп К. Дік",
        "birth_year": 1928,
        "death_year": 1982,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "Hugo Award (1963), Засновник премії Philip K. Dick Award",
        "trope_influence": "Розпад реальності, симулякри, андроїди з питанням людяності (Voight-Kampff), параноя сприйняття",
        "bio_summary": "Культовий візіонер метафізичної фантастики. Творець 'Чи мріють андроїди про електричних овець?', 'Людина у високому замку', 'Убік'. Досліджував крихкість людської психіки та суб'єктивної реальності."
    },
    {
        "slug": "robert-a-heinlein",
        "name_orig": "Robert A. Heinlein",
        "name_ukr": "Роберт А. Гайнлайн",
        "birth_year": 1907,
        "death_year": 1988,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "4 Hugo Awards for Best Novel, First Grand Master of SF",
        "trope_influence": "Слово 'grok' (осягнути/злитися), 'TANSTAAFL' (безкоштовних обідів не буває), силова броня (power armor), десантники",
        "bio_summary": "Декан американської наукової фантастики. Автор романів 'Зоряний десант', 'Чужинець на чужій землі', 'Місяць — суворий володар'. Ввів стандарти наукової достовірності в описі космічних польотів."
    },
    {
        "slug": "greg-egan",
        "name_orig": "Greg Egan",
        "name_ukr": "Ґреґ Іґан",
        "birth_year": 1961,
        "death_year": None,
        "country": "Australia",
        "primary_language": "en",
        "cult_tier": 2,
        "awards_summary": "Hugo Award, Locus, John W. Campbell Memorial Award Winner",
        "trope_influence": "Ультратверда квантова та математична НФ; цифрове безсмертя, квантова космологія, перепрограмування мозку",
        "bio_summary": "Видатний австралійський математик і письменник-затворник, беззаперечний лідер сучасної Hard SF. Шедеври 'Permutation City', 'Diaspora', 'Axiomatic' розширюють межі розуміння фізики та свідомості."
    },
    {
        "slug": "peter-watts",
        "name_orig": "Peter Watts",
        "name_ukr": "Пітер Воттс",
        "birth_year": 1958,
        "death_year": None,
        "country": "Canada",
        "primary_language": "en",
        "cult_tier": 2,
        "awards_summary": "Hugo Award, Seiun Award Winner; культовий статус у нейробіологів",
        "trope_influence": "Свідомість як еволюційний дефект; розум без самосвідомості ('Scramblers'); біоінженерні вампіри",
        "bio_summary": "Канадський морський біолог і автор найглибшого нейрофілософського НФ-роману XXI століття 'Blindsight' (Сліпобачення). Досліджує природу розуму, інтелект без свідомості та чужинність космосу."
    },
    {
        "slug": "dan-simmons",
        "name_orig": "Dan Simmons",
        "name_ukr": "Ден Сіммонс",
        "birth_year": 1948,
        "death_year": None,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "Hugo, Locus, British Science Fiction Award, World Fantasy",
        "trope_influence": "Гробниці Часу, Шрайк, портали фаркастерів (farcasters), ТехноЦентр автономних ШІ",
        "bio_summary": "Автор тетралогії 'Пісні Гіперіона' — вершини сучасної літературної космічної опери, яка поєднала поезію Джона Кітса, фізику простору-часу та теологію Тейяра де Шардена."
    },
    {
        "slug": "ted-chiang",
        "name_orig": "Ted Chiang",
        "name_ukr": "Тед Чан",
        "birth_year": 1967,
        "death_year": None,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 2,
        "awards_summary": "4 Hugo, 4 Nebula, 4 Locus, Campbell Award Winner (найвищий відсоток нагород на оповідання)",
        "trope_influence": "Нелінійний час гептаподів (гіпотеза Сепіра-Ворфа), філософська філологія, механічний креаціонізм",
        "bio_summary": "Геніальний автор малої форми. Його повість 'Story of Your Life' лягла в основу фільму 'Прибуття' (Arrival). Кожен його текст — вивірений філософський діамант."
    },
    {
        "slug": "liu-cixin",
        "name_orig": "Liu Cixin",
        "name_ukr": "Лю Цисінь",
        "birth_year": 1963,
        "death_year": None,
        "country": "China",
        "primary_language": "zh",
        "cult_tier": 1,
        "awards_summary": "Hugo Award Winner (перший автор з Азії, що отримав Hugo за найкращий роман)",
        "trope_influence": "Теорія Темного Лісу (Dark Forest), софони (sophons), колапс розмірностей простору",
        "bio_summary": "Китайський інженер-енергетик, автор трилогії 'Пам'ять про минуле Землі' (Завдання трьох тіл), що стала всесвітнім культурним феноменом та новим каноном глобальної космічної опери."
    },
    {
        "slug": "vernor-vinge",
        "name_orig": "Vernor Vinge",
        "name_ukr": "Вернор Віндж",
        "birth_year": 1944,
        "death_year": 2024,
        "country": "USA",
        "primary_language": "en",
        "cult_tier": 1,
        "awards_summary": "5 Hugo Awards (3 за найкращий роман: 'A Fire Upon the Deep', 'A Deepness in the Sky', 'Rainbows End')",
        "trope_influence": "Концепт технологічної сингулярності (Technological Singularity), Зони думки (Zones of Thought), телекомунікаційний ройовий розум",
        "bio_summary": "Професор комп'ютерних наук та математики. Творець сучасної теорії технологічної сингулярності та шедеврів далекої космології."
    }
]

WORKS_SEED: List[Dict[str, Any]] = [
    {
        "slug": "rur-rossums-universal-robots",
        "author_slug": "karel-capek",
        "title_orig": "R.U.R. (Rossum's Universal Robots)",
        "title_ukr": "Р.У.Р. (Россумові універсальні роботи)",
        "year": 1920,
        "original_lang": "cs",
        "form": "Play",
        "subgenres": ["Proto-SF", "Philosophical Drama", "Artificial Life"],
        "awards": ["All-Time Canon Induction", "Porges Century Landmark"],
        "canon_inclusions": ["Porges Century Canon", "Locus All-Time Best", "SF Masterworks"],
        "trope_maker": True,
        "synopsis": "П'єса, яка ввела у світову мову слово 'робот'. На острові вчений Россум та його фабрика виготовляють штучних біологічних людей для полегшення праці людства, проте машини повстають і винищують своїх творців.",
        "text_filename": "rur.txt"
    },
    {
        "slug": "neuromancer",
        "author_slug": "william-gibson",
        "title_orig": "Neuromancer",
        "title_ukr": "Нейромансер",
        "year": 1984,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Cyberpunk", "Hard SF", "Artificial Intelligence"],
        "awards": ["Hugo Winner", "Nebula Winner", "Philip K. Dick Winner"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best", "r/printSF Top Tier"],
        "trope_maker": True,
        "synopsis": "Основоположний роман кіберпанку. Хакер Кейс наймається таємничим Армітажем для здійснення віртуального проникнення у надзахищений штучний інтелект Вінтерм'ют корпорації Тесьє-Ешпул.",
        "text_filename": "neuromancer.txt"
    },
    {
        "slug": "the-dispossessed",
        "author_slug": "ursula-k-le-guin",
        "title_orig": "The Dispossessed",
        "title_ukr": "Знедолені",
        "year": 1974,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Social SF", "Anarchist Utopia", "Hainish Cycle"],
        "awards": ["Hugo Winner", "Nebula Winner", "Locus Winner"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best"],
        "trope_maker": True,
        "synopsis": "Фізик Шевек намагається створити загальну теорію часовості, яка уможливить створення миттєвого зв'язку — ансибла (ansible), балансуючи між анархічним світом Анаррес та капіталістичним Уррасом.",
        "text_filename": "the_dispossessed.txt"
    },
    {
        "slug": "rocannons-world",
        "author_slug": "ursula-k-le-guin",
        "title_orig": "Rocannon's World",
        "title_ukr": "Світ Роканнона",
        "year": 1966,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Hainish Cycle", "First Contact", "Planetary Romance"],
        "awards": ["Hainish Cycle Inaugural Novel"],
        "canon_inclusions": ["SF Masterworks"],
        "trope_maker": True,
        "synopsis": "Перший твір Гайнського циклу і перша в історії світової літератури фіксація терміна 'ansible' (пристрій миттєвого підпросторового зв'язку).",
        "text_filename": "rocannons_world.txt"
    },
    {
        "slug": "dune",
        "author_slug": "frank-herbert",
        "title_orig": "Dune",
        "title_ukr": "Дюна",
        "year": 1965,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Space Opera", "Ecological SF", "Planetary Romance"],
        "awards": ["Hugo Winner", "Nebula Winner (Inaugural)"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best (#1 Novel)", "r/printSF Top Tier"],
        "trope_maker": True,
        "synopsis": "Велична сага про пустельну планету Арракіс, прянощі, гігантських хробаків та перетворення юного Пола Атрідса на месію фрименів Муад'Діба.",
        "text_filename": "dune.txt"
    },
    {
        "slug": "solaris",
        "author_slug": "stanislaw-lem",
        "title_orig": "Solaris",
        "title_ukr": "Соляріс",
        "year": 1961,
        "original_lang": "pl",
        "form": "Novel",
        "subgenres": ["First Contact", "Philosophical SF", "Psychological Drama"],
        "awards": ["All-Time Canon Polish Literature", "World SF Masterpiece"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best"],
        "trope_maker": True,
        "synopsis": "Психолог Кріс Кельвін прибуває на станцію над живим плазматичним океаном планети Соляріс. Океан матеріалізує найпотаємніші, болісні спогади та видіння дослідників, демонструючи трагічну прірву між людським розумом і нелюдським космосом.",
        "text_filename": "solaris.txt"
    },
    {
        "slug": "foundation",
        "author_slug": "isaac-asimov",
        "title_orig": "Foundation",
        "title_ukr": "Фундація",
        "year": 1951,
        "original_lang": "en",
        "form": "Novel / Fix-up",
        "subgenres": ["Galactic Empire", "Sociological SF", "Hard SF"],
        "awards": ["Special Hugo: Best All-Time Series"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best"],
        "trope_maker": True,
        "synopsis": "Математик Гарі Селдон розробляє науку психоісторію, передбачає крах Галактичної Імперії та засновує Фундацію на краю галактики, щоб скоротити епоху варварства з тридцяти тисяч років до однієї тисячі.",
        "text_filename": "foundation.txt"
    },
    {
        "slug": "2001-a-space-odyssey",
        "author_slug": "arthur-c-clarke",
        "title_orig": "2001: A Space Odyssey",
        "title_ukr": "2001: Космічна одіссея",
        "year": 1968,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Hard SF", "First Contact", "Cosmic Transcendence"],
        "awards": ["Hugo Nominee", "Cinema Landmark"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best"],
        "trope_maker": True,
        "synopsis": "Чорний моноліт знайдено на Місяці. Експедиція корабля 'Дискавері' вирушає до Юпітера/Сатурна під контролем комп'ютера HAL 9000, стикаючись з бунтом штучного розуму та космічним переродженням людини.",
        "text_filename": "2001_space_odyssey.txt"
    },
    {
        "slug": "ubik",
        "author_slug": "philip-k-dick",
        "title_orig": "Ubik",
        "title_ukr": "Убік",
        "year": 1969,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Metaphysical SF", "Psychic Espionage", "Time Regression"],
        "awards": ["Time Magazine 100 Greatest Novels"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best"],
        "trope_maker": True,
        "synopsis": "Джо Чіп та антипсі-фахівці переживають теракт на Місяці. Світ довкола них починає незворотно деградувати в часі, а єдиним порятунком є загадкова субстанція у спреї — 'Убік'.",
        "text_filename": "ubik.txt"
    },
    {
        "slug": "hyperion",
        "author_slug": "dan-simmons",
        "title_orig": "Hyperion",
        "title_ukr": "Гіперіон",
        "year": 1989,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Space Opera", "New Weird", "Far-Future"],
        "awards": ["Hugo Winner", "Locus Winner", "BSFA Winner"],
        "canon_inclusions": ["SF Masterworks", "NPR Top 100 SF", "Locus All-Time Best", "r/printSF Top Tier"],
        "trope_maker": True,
        "synopsis": "Семеро паломників вирушають на далеку планету Гіперіон до Гробниць Часу, що рухаються назад у часі, та до металевого володаря болю — Шрайка, розповідаючи свої вражаючі історії у стилі Кентерберійських оповідей.",
        "text_filename": "hyperion.txt"
    },
    {
        "slug": "blindsight",
        "author_slug": "peter-watts",
        "title_orig": "Blindsight",
        "title_ukr": "Сліпобачення",
        "year": 2006,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Hard SF", "Neuro-philosophy", "First Contact"],
        "awards": ["Hugo Nominee", "Locus Nominee", "Seiun Winner"],
        "canon_inclusions": ["r/printSF Top Tier", "Modern Hard SF Canon"],
        "trope_maker": True,
        "synopsis": "Екіпаж транслюдей та реанімованого генетичного вампіра на кораблі 'Тезей' відправлений до Хмари Оорта на зустріч з чужинським об'єктом 'Роршах', щоб з'ясувати шокуючу істину: свідомість є не вершиною еволюції, а її шкідливим баластом.",
        "text_filename": "blindsight.txt"
    },
    {
        "slug": "the-three-body-problem",
        "author_slug": "liu-cixin",
        "title_orig": "The Three-Body Problem",
        "title_ukr": "Проблема трьох тіл",
        "year": 2008,
        "original_lang": "zh",
        "form": "Novel",
        "subgenres": ["Hard SF", "Cosmic Sociology", "First Contact"],
        "awards": ["Hugo Winner", "Nebula Nominee", "Locus Nominee"],
        "canon_inclusions": ["Modern Masterworks", "r/printSF Top Tier", "NPR Top 100 SF"],
        "trope_maker": True,
        "synopsis": "Під час Культурної революції в Китаї секретний військовий проєкт посилає сигнали в космос. Їх перехоплює цивілізація Трисоляріса, чия планета гине у хаотичній системі трьох зірок.",
        "text_filename": "three_body_problem.txt"
    },
    {
        "slug": "a-fire-upon-the-deep",
        "author_slug": "vernor-vinge",
        "title_orig": "A Fire Upon the Deep",
        "title_ukr": "Полум'я над безоднею",
        "year": 1992,
        "original_lang": "en",
        "form": "Novel",
        "subgenres": ["Hard SF", "Space Opera", "Singularity"],
        "awards": ["Hugo Winner", "Nebula Nominee", "Campbell Nominee"],
        "canon_inclusions": ["SF Masterworks", "Locus All-Time Best", "r/printSF Top Tier"],
        "trope_maker": True,
        "synopsis": "Галактика поділена на 'Зони думки' — від Повільної зони (де навіть світло повільне і ШІ неможливий) до Безодні (надрозум). Випадково розбуджена стародавня Загибель загрожує знищити всі розумні цивілізації.",
        "text_filename": "fire_upon_the_deep.txt"
    }
]


def seed_database(db):
    """Populates the database with initial cult authors, works, and calculated Cult Scores."""
    author_id_map = {}

    # 1. Insert Authors
    for a_data in AUTHORS_SEED:
        author = Author(
            slug=a_data["slug"],
            name_orig=a_data["name_orig"],
            name_ukr=a_data["name_ukr"],
            birth_year=a_data["birth_year"],
            death_year=a_data["death_year"],
            country=a_data["country"],
            primary_language=a_data["primary_language"],
            cult_tier=a_data["cult_tier"],
            cult_score=0.0,
            awards_summary=a_data["awards_summary"],
            trope_influence=a_data["trope_influence"],
            bio_summary=a_data["bio_summary"]
        )
        a_id = db.insert_author(author)
        author_id_map[a_data["slug"]] = a_id

    # 2. Insert Works with Cult Score Calculation
    author_works_scores: Dict[str, List[float]] = {}

    for w_data in WORKS_SEED:
        a_slug = w_data["author_slug"]
        author_id = author_id_map.get(a_slug)
        if not author_id:
            continue

        cult_score = CultRanker.calculate_work_cult_score(
            year=w_data["year"],
            awards=w_data["awards"],
            canon_inclusions=w_data["canon_inclusions"],
            trope_maker=w_data.get("trope_maker", False)
        )

        work = Work(
            slug=w_data["slug"],
            author_id=author_id,
            title_orig=w_data["title_orig"],
            title_ukr=w_data["title_ukr"],
            year=w_data["year"],
            original_lang=w_data["original_lang"],
            form=w_data["form"],
            subgenres=w_data["subgenres"],
            awards=w_data["awards"],
            canon_inclusions=w_data["canon_inclusions"],
            cult_score=cult_score,
            synopsis=w_data["synopsis"],
            has_full_text=False,
            text_path=None,
            word_count=0,
            research_status="pending"
        )
        db.insert_work(work)

        if a_slug not in author_works_scores:
            author_works_scores[a_slug] = []
        author_works_scores[a_slug].append(cult_score)

    # 3. Recalculate Author Cult Scores based on their magnum opuses
    for a_data in AUTHORS_SEED:
        slug = a_data["slug"]
        scores = author_works_scores.get(slug, [])
        author_cult_score = CultRanker.calculate_author_cult_score(
            tier=a_data["cult_tier"],
            works_cult_scores=scores,
            coined_concepts_count=3 if a_data["cult_tier"] == 1 else 1
        )
        # Update author in db
        author = Author(
            slug=slug,
            name_orig=a_data["name_orig"],
            name_ukr=a_data["name_ukr"],
            birth_year=a_data["birth_year"],
            death_year=a_data["death_year"],
            country=a_data["country"],
            primary_language=a_data["primary_language"],
            cult_tier=a_data["cult_tier"],
            cult_score=author_cult_score,
            awards_summary=a_data["awards_summary"],
            trope_influence=a_data["trope_influence"],
            bio_summary=a_data["bio_summary"]
        )
        db.insert_author(author)
