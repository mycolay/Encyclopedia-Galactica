import hashlib
from modules.lexicography.entity_checks import locate, check_entity


def test_whitespace_maps_back_to_original_utf8_bytes():
    text='Початок: creature\r\n  open.'
    result,error=locate(text,'creature open')
    assert error is None
    raw=text.encode()[result['local_byte_start']:result['local_byte_start']+result['byte_len']]
    assert raw==b'creature\r\n  open'
    assert hashlib.sha256(raw).hexdigest()==result['quote_sha256']


def test_no_punctuation_or_word_repair():
    assert locate('eye; open','eye open')[1]=='quote_absent'
    assert locate('creature opens','creature open.')[1]=='quote_absent'


def test_repeated_quote_requires_disambiguation():
    assert locate('eye open; eye\nopen','eye open')[1]=='quote_ambiguous'


def test_placeholder_held_despite_valid_quote():
    item=dict(name='original designation',quote='instruments of life',kind='concept',description_uk='Опис',epistemic='explicit')
    result=check_entity(item,dict(text='instruments of life',byte_start=10))
    assert 'name_not_in_original' in result['issues']
    assert result['status']=='held'


def test_name_substring_does_not_count():
    item=dict(name='Gene',quote='Geneva',kind='place',description_uk='Опис',epistemic='explicit')
    assert 'name_not_in_original' in check_entity(item,dict(text='Geneva',byte_start=0))['issues']


def test_valid_source_is_not_semantic_validation():
    item=dict(name='Ingolstadt',quote='university of Ingolstadt',kind='place',description_uk='Хибний опис',epistemic='explicit')
    result=check_entity(item,dict(text='university of Ingolstadt',byte_start=100))
    assert result['status']=='source_grounded_editorial_pending'
    assert result['semantic_validation'] is False
