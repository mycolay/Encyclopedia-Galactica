import pytest
from scripts.run_world_pilot import ground

def test_quote_offset_utf8_and_no_semantic_promotion():
    result=ground({'entities':[dict(name='місто',kind='place',description_uk='Неперевірений опис',quote='місто',epistemic='explicit')]},dict(text='Це місто.',byte_start=100))
    item=result['accepted'][0]
    assert item['byte_start']==100+len('Це '.encode())
    assert item['byte_len']==len('місто'.encode())
    assert item['entailment']=='not_verified'

def test_fabricated_quote_is_rejected():
    result=ground({'entities':[dict(name='X',kind='character',description_uk='Опис',quote='invented',epistemic='inferred')]},dict(text='original',byte_start=0))
    assert not result['accepted']
    assert result['rejected'][0]['reason']=='quote_not_exact_in_original'

def test_unknown_entity_type_fails():
    with pytest.raises(ValueError,match='invalid_type'):
        ground({'entities':[dict(name='X',kind='anything',description_uk='Опис',quote='X',epistemic='explicit')]},dict(text='X',byte_start=0))
