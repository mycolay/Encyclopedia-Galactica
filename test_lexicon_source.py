"""
Регресійні тести розбору посилань на Грінченка.

Обидві пастки знайдені на реальних даних 2026-09-06.
"""

from modules.lexicography.lexicon_source import (
    parse_citation,
    extract_headword,
    expected_volume,
    check_volume_consistency,
)


def test_cyrillic_roman_numerals():
    """
    У даних римські числівники писані КИРИЛИЧНОЮ І (U+0406), не латинською.
    Через це 11 із 14 посилань спершу взагалі не розпарсились.
    """
    assert parse_citation("Словарь Грінченка, т. ІІ, с. 417").volume == 2
    assert parse_citation("т. І, с. 242").volume == 1
    assert parse_citation("Словарь Грінченка, т. IV, с. 293").volume == 4  # латинська


def test_page_marker_optional():
    """У даних трапляється і «т. IV, с. 293», і «Грінченко І, 73» без «с.»."""
    c = parse_citation("За моделлю велетень, блазень (Грінченко І, 73).")
    assert c is not None and c.volume == 1 and c.page == 73


def test_no_citation_returns_none():
    assert parse_citation("складне слово: часо- + проходець") is None
    assert parse_citation("") is None


def test_volume_ranges():
    assert expected_volume("вісник") == 1     # В -> А-Ж
    assert expected_volume("лічильник") == 2  # Л -> З-Н
    assert expected_volume("палець") == 3     # П -> О-П
    assert expected_volume("сховище") == 4    # С -> Р-Я


def test_contradiction_detected_without_dictionary():
    """
    Найдешевша перевірка ловить вигадку без завантаження словника:
    «сховище» на «С» не може бути в томі 2.
    """
    c = parse_citation("Словарь Грінченка, т. ІІ, с. 417: за зразком сховище")
    c.headword = extract_headword("Словарь Грінченка, т. ІІ, с. 417: за зразком сховище")
    res = check_volume_consistency(c)
    assert res["verdict"] == "CONTRADICTED"
    assert res["expected_volume"] == 4


def test_plausible_when_volume_matches():
    text = "Словарь Грінченка, т. IV, с. 129: модель сіть"
    c = parse_citation(text)
    c.headword = extract_headword(text)
    assert check_volume_consistency(c)["verdict"] == "PLAUSIBLE"


def test_headword_extraction_forms():
    assert extract_headword("т. IV, с. 293: 'Трудникъ' — робітник") == "Трудникъ"
    assert extract_headword("Грінченко І, 243 (віщувати, віщий)") == "віщувати"
    assert extract_headword("Грінченко І, 237; за моделлю мовознавство") == "мовознавство"
