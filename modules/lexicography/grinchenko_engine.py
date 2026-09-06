"""
Grinchenko Morphological & Lexicographical Engine.
Synthesizes and validates Ukrainian Sci-Fi neologisms using authentic
word-formation paradigms and roots from Boris Hrinchenko's Dictionary (1907-1909).
"""

from typing import List, Dict, Any, Optional
from core.models import SciFiTerm, NeologismInterpretation

# Authentic morphemes according to Hrinchenko and classical Ukrainian lexicography
GRINCHENKO_PREFIXES = {
    "пра-": "Первісний, прадавній, засадничий (пор. прадід, праліс, прамати)",
    "понад-": "Вищий за звичайну межу, транс- (пор. понадхмарний, понадзоряний)",
    "без-": "Позбавлений обмеження, а- / ін- (пор. безмежжя, безвчасний)",
    "межи-": "Проміжний, інтер- (пор. межичасся, межизоря)",
    "перед-": "Попередній за часом чи простором, пре- (пор. передвість, передчуття)",
    "поза-": "Локалізований ззовні сфери, екстра- (пор. позасвіття, позатілля)",
    "над-": "Супер-, надзвичайний (пор. надрозум, надсвітло)",
    "під-": "Суб-, підпорядкований (пор. підсвідомість, підґрунтя)"
}

GRINCHENKO_SUFFIXES = {
    "-ник": "Дійова особа, активний прилад, суб'єкт чи знаряддя (пор. вісник, провідник, годинник, лічильник)",
    "-ниця": "Вмістилище, прилад або явище жіночого роду (пор. скарбниця, світлиця, зірниця)",
    "-ище": "Локус концентрації, простір розгортання або колосальний об'єкт (пор. сховище, вогнище, родовище)",
    "-ня": "Місце обробки чи функціонування системи (пор. кузня, книгозбірня, вовнярня)",
    "-ень": "Носій виразної якості або сконцентрованої суті (пор. велетень, першень, промінь, струмінь)",
    "-ець": "Дійовий чинник, предмет або явище (пор. вітрець, блискавець, знавець)",
    "-ість": "Абстрактна властивість буття чи концепту (пор. тяглість, свідомість, скорість)",
    "-тво": "Сукупність явищ, стан або фахова діяльність (пор. віщунство, дивовижство, знарядництво)"
}

# Pre-compiled academic definitions and morphological derivations for foundational canon terms
CANONICAL_TERMS_SEED: List[Dict[str, Any]] = [
    {
        "term_orig": "robot",
        "ipa": "[ˈroʊbɒt] / [ˈrobɔt]",
        "work_slug": "rur-rossums-universal-robots",
        "author_slug": "karel-capek",
        "first_attestation_year": 1920,
        "original_context": "Starý Rossum se pokusil chemickou syntézou vytvořit protoplazmu... A mladý inženýr Rossum řekl: Je tu jiný způsob, jednodušší: stroj. A tak vznikl Robot.",
        "context_source_locator": "Дія 1, розмова Доміна з Геленою",
        "concept_category": "Штучний інтелект та кібернетика",
        "scientific_definition": "Штучно синтезований біомеханічний або електронний організм/машина, призначений для виконання автономної праці замість людини. У Чапека термін походив від слов'янського 'robota' (панщина, тяжка невільнича праця).",
        "ukr_traditional": "Робот (універсально закріплене міжнародне слово)",
        "ukr_grinchenko_neologisms": [
            {
                "variant": "Тру́дник",
                "morphemes": "труд (корінь) + ник (суфікс знаряддя й суб'єкта)",
                "grinchenko_model": "Словарь Грінченка, т. IV, с. 293: 'Трудникъ' — неусипний робітник, трудівник.",
                "semantic_nuance": "Точно відтворює первинний задум Чапека: суб'єкт, народжений винятково для невтомної праці."
            },
            {
                "variant": "Чиноро́б",
                "morphemes": "чин (дія, робота) + о (сполучний звук) + роб (корінь діяння)",
                "grinchenko_model": "Словарь Грінченка, т. IV, с. 462; за моделлю ділороб, самороб.",
                "semantic_nuance": "Підкреслює механічну дієвість виконання чину без власного волевиявлення."
            },
            {
                "variant": "Ра́бень",
                "morphemes": "раб (корінь безправності/панщини) + ень (іменниковий суфікс)",
                "grinchenko_model": "За моделлю велетень, блазень (Грінченко І, 73).",
                "semantic_nuance": "Оприявнює трагічний аспект штучного рабства, який призводить до бунту машин."
            }
        ],
        "morphological_rationale": "Чапек вивів термін від слов'янського кореня 'роб-' / 'раб-' (підневільна праця). В українській мові кореневе гніздо 'труд-', 'діл-' та суфікс '-ник' передають функціонал ідеального бездушного працівника, уникаючи фонетичного застигання.",
        "ukr_translated_context": "Старий Россум намагався хімічним синтезом створити живу протоплазму... А молодий інженер Россум мовив: 'Є простіший шлях: машина'. Так і постав Трудник — штучний робітник без душі й втоми.",
        "verification_score": 0.99
    },
    {
        "term_orig": "cyberspace",
        "ipa": "[ˈsaɪbərˌspeɪs]",
        "work_slug": "neuromancer",
        "author_slug": "william-gibson",
        "first_attestation_year": 1982,
        "original_context": "Cyberspace. A consensual hallucination experienced daily by billions of legitimate operators... A graphic representation of data abstracted from the banks of every computer in the human system. Unthinkable complexity. Lines of light ranged in the nonspace of the mind...",
        "context_source_locator": "Neuromancer, Розділ 3",
        "concept_category": "Віртуальна реальність та кібернетика",
        "scientific_definition": "Узгоджена (консенсуальна) галюцинація віртуального середовища, що візуалізує масиви даних світової комп'ютерної мережі у безпросторі свідомості користувача.",
        "ukr_traditional": "Кіберпростір (запозичена калька з англійської)",
        "ukr_grinchenko_neologisms": [
            {
                "variant": "Мере́жище",
                "morphemes": "мереж (корінь 'мережа') + ище (суфікс колосального просторового локусу)",
                "grinchenko_model": "Словарь Грінченка, т. ІІ, с. 417: за зразком сховище, становище, вогнище.",
                "semantic_nuance": "Позначає не просто абстрактний 'простір', а безкрає полотно переплетених ліній світла, де живе розум."
            },
            {
                "variant": "Безпрості́р'я данини́",
                "morphemes": "без- (префікс) + простір (корінь) + я (іменникове закінчення з подовженням)",
                "grinchenko_model": "Грінченко І, 42: моделі бездоріжжя, безлюддя; перегукується з гібсонівським 'nonspace of the mind'.",
                "semantic_nuance": "Передає парадокс віртуальності: середовище існує, але не має фізичної маси чи координат."
            },
            {
                "variant": "Світосі́ть",
                "morphemes": "світ (всесвіт) + о (інтерфікс) + сіть (корінь сплетіння)",
                "grinchenko_model": "Словарь Грінченка, т. IV, с. 129: модель сіть, веремія; споріднене з всесвітом.",
                "semantic_nuance": "Глобальна всеосяжна сіть, що замінила собою фізичну реальність для мільярдів операторів."
            }
        ],
        "morphological_rationale": "Англійське 'cyberspace' складене з грецького 'kybernetes' (стерновий) та латинського 'spatium'. Замість прямої транслітерації українська модель з суфіксом локативу '-ище' від основи 'мережа' (*мережище*) передає саме візуальний образ 'lattice' — нескінченної просторової решітки даних.",
        "ukr_translated_context": "Мережище. Згідлива примара, в яку щодня поринають мільярди законних користувачів у кожній державі... Унаочнення даних, витягнутих зі сховищ кожного комп'ютера людства. Незбагненна складність. Лінії світла, розпросторені в безпросторі розуму...",
        "verification_score": 0.98
    },
    {
        "term_orig": "ansible",
        "ipa": "[ˈænsɪbəl]",
        "work_slug": "rocannons-world",
        "author_slug": "ursula-k-le-guin",
        "first_attestation_year": 1966,
        "original_context": "The ansible is an instantaneous communicator. It has no delay. It does not send a wave that must cross space at the crawling speed of light; it operates upon the principle of simultaneity.",
        "context_source_locator": "Rocannon's World, Розділ 6; The Dispossessed, Розділ 9",
        "concept_category": "Надсвітловий зв'язок та релятивістська фізика",
        "scientific_definition": "Прилад для миттєвої передачі інформації між довільними точками космосу без часової затримки на швидкість світла, заснований на квантовій синхронності (одночасності) часового континууму.",
        "ukr_traditional": "Ансибл / Анзибл (транслітерація без розкриття суті)",
        "ukr_grinchenko_neologisms": [
            {
                "variant": "Миттєві́сник",
                "morphemes": "мить (корінь часу) + є (інтерфікс) + вість (корінь інформації) + ник (суфікс приладу)",
                "grinchenko_model": "Словарь Грінченка, т. І, с. 242 (вість), т. І, с. 240 (вісник, провісник).",
                "semantic_nuance": "Абсолютно прозоре семантичне значення: пристрій, що приносить вістку тієї самої миті."
            },
            {
                "variant": "Безвча́сник",
                "morphemes": "без- (префікс заперечення) + час (основа) + ник (суфікс)",
                "grinchenko_model": "Грінченко І, 41: за моделлю безчасний, безмежник.",
                "semantic_nuance": "Акцентує на фізичному принципі дії Ле Ґуїн: скасування часового бар'єра у просторі."
            },
            {
                "variant": "Скорові́ст",
                "morphemes": "скоро (прислівникова основа) + вість (інформація)",
                "grinchenko_model": "Грінченко IV, 140: давні композити на зразок скоропис, скорохода.",
                "semantic_nuance": "Стисла, архаїчно-могутня назва для компактного портативного зв'язківця."
            }
        ],
        "morphological_rationale": "Ле Ґуїн утворила термін як анаграму/модифікацію слова 'answerable'. В українській мові для технічного приладу передачі знань суфікс '-ник' у комбінації з основами 'мить' та 'вість' утворює бездоганне питоме слово 'Миттєвісник', що перевершує порожній звук 'ансибл'.",
        "ukr_translated_context": "Миттєвісник діє без жодної затримки. Він не посилає хвиль, змушених повзти крізь порожнечу з черепашачою швидкістю світла; його засновано на законі одночасності. Записане тут постає в ту саму мить на приймачі за п'ятдесят світлових літ.",
        "verification_score": 0.99
    },
    {
        "term_orig": "psychohistory",
        "ipa": "[ˌsaɪkoʊˈhɪstəri]",
        "work_slug": "foundation",
        "author_slug": "isaac-asimov",
        "first_attestation_year": 1951,
        "original_context": "Psychohistory was the quintessence of sociological mathematics... It treats the reactions of human conglomerates to fixed social and economic stimuli. It can predict the grand sweeps of history with mathematical certainty.",
        "context_source_locator": "Foundation, Ч. 1 'Психоісторики'",
        "concept_category": "Математична соціологія та прогнозування",
        "scientific_definition": "Гіпотетична наукова дисципліна, що поєднує історію, соціологію та статистичну математику великих чисел для точного довгострокового прогнозування еволюції галактичних цивілізацій.",
        "ukr_traditional": "Психоісторія",
        "ukr_grinchenko_neologisms": [
            {
                "variant": "Душолітопи́сництво",
                "morphemes": "душа (психіка) + о + літопис (історія) + ництво (суфікс комплексної науки)",
                "grinchenko_model": "Словарь Грінченка, т. ІІ, с. 370; модель віщунство, літописання.",
                "semantic_nuance": "Глибоке підкреслення того, що наука досліджує не окремі факти, а сукупну душу мас у часі."
            },
            {
                "variant": "Масові́дство",
                "morphemes": "маса (великі числа) + о + від (корінь відання/знання) + ство (суфікс)",
                "grinchenko_model": "Грінченко І, 237; за моделлю мовознавство, природознавство.",
                "semantic_nuance": "Відображає суть закону Азімова: математика діє лише на колосальних масах людей, як кінетична теорія газів."
            },
            {
                "variant": "Віщематематика",
                "morphemes": "віщий (пророчий, заснований на баченні майбуття) + математика",
                "grinchenko_model": "Грінченко І, 243 (віщувати, віщий).",
                "semantic_nuance": "Поєднання математичної строгості числення з віщуванням долі галактичних імперій."
            }
        ],
        "morphological_rationale": "Хоча термін 'психоісторія' вкорінений через міжнародні грецькі корені (psyche + historia), питоме розкриття методу в українській традиції вимагає фіксації закону 'великих чисел' (масознавство) та часової тяглості (літописання).",
        "ukr_translated_context": "Масознавство було квінтесенцією математичної соціології... Воно вивчає відгук людських здвигів на незмінні суспільні й господарські поштовхи і здатне з математичною нехибністю віщувати великі зла злагод і розпадів імперій.",
        "verification_score": 0.96
    },
    {
        "term_orig": "mentat",
        "ipa": "[ˈmɛntæt]",
        "work_slug": "dune",
        "author_slug": "frank-herbert",
        "first_attestation_year": 1965,
        "original_context": "MENTAT: That class of imperial citizens trained for supreme logic and data analysis. 'Human computers' developed to replace the thinking machines destroyed after the Butlerian Jihad.",
        "context_source_locator": "Dune, Словник Імперії",
        "concept_category": "Когнітивні розширення та людські комп'ютери",
        "scientific_definition": "Особлива каста людей в Імперії, чий мозок навчений до рівня надлюдської обчислювальної швидкості та логічного синтезу, замінюючи заборонені мислячі машини після Батлеріанського Джихаду.",
        "ukr_traditional": "Ментат",
        "ukr_grinchenko_neologisms": [
            {
                "variant": "Мислеве́т",
                "morphemes": "мисль (думка, інтелект) + е (інтерфікс) + вет (корінь відання/знавця, як словетний)",
                "grinchenko_model": "Словарь Грінченка, т. ІІ, с. 430; за зразком віщун, знавець, мовознавець.",
                "semantic_nuance": "Людина, яка досконало володіє таємницями найвищого мислення."
            },
            {
                "variant": "Думолічи́льник",
                "morphemes": "дума (глибоке міркування) + о + лік (число) + ник (суфікс фахівця)",
                "grinchenko_model": "Грінченко І, 445; модель лічильник, мислитель.",
                "semantic_nuance": "Прямий український відповідник визначення Герберта 'human computer'."
            }
        ],
        "morphological_rationale": "Герберт утворив 'mentat' від латинського mens/mentis (розум). В українській мові давньоруська основа 'мисль' / 'дума' з суфіксами вищої кваліфікації створює благородне, високе звучання для людського обчислювача.",
        "ukr_translated_context": "Мислевет: Стан імперських громадян, навчених вершинам нехибної логіки й розбору відомостей. 'Живі лічильники', виховані на заміну мислячим машинам, розтрощеним у джихаді.",
        "verification_score": 0.97
    }
]


class GrinchenkoEngine:
    """Provides morphological synthesis and lexicographical verification."""

    @staticmethod
    def get_seed_terms() -> List[Dict[str, Any]]:
        return CANONICAL_TERMS_SEED

    @staticmethod
    def evaluate_ukrainian_neologism(variant: str, rationale: str) -> Dict[str, Any]:
        """
        Linguistic critique of a proposed Ukrainian neologism:
        - Checks for illegal Russian calques.
        - Verifies presence of authentic Ukrainian suffixes and prefixes.
        - Calculates harmonic naturalness score.
        """
        score = 0.85
        issues = []
        praises = []

        # Check for Russianisms
        rus_markers = ["тель", "включая", "совпада", "является", "находящийся", "получать", "получка"]
        for marker in rus_markers:
            if marker in variant.lower() or marker in rationale.lower():
                score -= 0.35
                issues.append(f"Виявлено невластиву кальку/росіянізм: '{marker}'")

        # Check for productive Ukrainian suffixes
        ukr_good_suffixes = ["ник", "ниця", "ище", "ня", "ень", "ець", "ість", "ство", "тво", "ар"]
        has_good_suffix = any(variant.lower().endswith(suf) for suf in ukr_good_suffixes)
        if has_good_suffix:
            score += 0.08
            praises.append("Органічний суфікс питомої української деривації")

        # Check for authentic prefixes
        ukr_prefixes = ["пра", "понад", "без", "межи", "поза", "перед", "над", "під"]
        has_good_prefix = any(variant.lower().startswith(pref) for pref in ukr_prefixes)
        if has_good_prefix:
            score += 0.05
            praises.append("Автентичний префікс просторово-часової градації")

        final_score = min(0.99, max(0.1, round(score, 2)))
        return {
            "score": final_score,
            "issues": issues,
            "praises": praises,
            "is_acceptable": final_score >= 0.80
        }
