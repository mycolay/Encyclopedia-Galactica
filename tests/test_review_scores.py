from copy import deepcopy
import pytest
from modules.lexicography.review_scores import agreement,compare,validate,SCALES

def fixture():
    return dict(reviewer=dict(name=None,source_language_competence=None,ukrainian_competence=None,
        philological_experience=None,conflicts=None),items=[dict(id='one',term='X',variant='Y',
        phase='development_review',contexts=[],context_sufficient=None,relevance=None,relevance_reason='',
        recognized_provenance=None,scores={s:None for s in SCALES},na_reasons={},comment='')])

def filled(name):
    f=fixture();f['reviewer']={k:'fixture' for k in f['reviewer']};f['reviewer']['name']=name
    f['reviewer']['role']='human'
    f['items'][0].update(context_sufficient=True,relevance='include',relevance_reason='fixture',
        recognized_provenance=False,scores={s:3 for s in SCALES})
    return f

def test_known_weighted_kappa():
    result=agreement([(0,0),(1,2),(2,1),(3,3)])
    assert result['weighted_kappa']==pytest.approx(.6)
    assert result['exact']==.5 and result['within_one']==1

def test_degenerate_and_empty_are_not_perfect_scores():
    assert agreement([(3,3),(3,3)])['weighted_kappa'] is None
    assert agreement([])['exact'] is None

def test_unfilled_forms_cannot_become_results():
    f=fixture();r=compare(f,f,f,f)
    assert r['status']=='not_ready'
    assert r['phases']['development_review']['scales']['semantics']['n']==0

def test_protected_context_cannot_change():
    f=filled('A');f['items'][0]['contexts']=['changed']
    with pytest.raises(ValueError,match='protected_content_changed'):validate(f,fixture())

def test_duplicate_ids_rejected():
    f=fixture();f['items'].append(deepcopy(f['items'][0]))
    with pytest.raises(ValueError,match='duplicate_ids'):validate(f,fixture())

@pytest.mark.parametrize('value',[True,4,-1,1.5,'3'])
def test_invalid_score_rejected(value):
    f=filled('A');f['items'][0]['scores']['semantics']=value
    with pytest.raises(ValueError,match='invalid_score'):validate(f,fixture())

def test_same_person_not_two_reviewers():
    with pytest.raises(ValueError,match='same_reviewer'):compare(filled('A'),filled(' a '),fixture(),fixture())

def test_na_requires_reason_and_excluded_pairwise():
    a,b=filled('A'),filled('B');a['items'][0]['scores']['style']=None
    assert compare(a,b,fixture(),fixture())['completed_first']==0
    a['items'][0]['na_reasons']['style']='not applicable'
    r=compare(a,b,fixture(),fixture())['phases']['development_review']
    assert r['scales']['style']['na_pairs']==1
    assert r['scales']['semantics']['n']==1
    assert r['arbitration'][0]['reasons']==['NA:style']

def test_large_difference_and_low_semantics_trigger_arbitration():
    a,b=filled('A'),filled('B');b['items'][0]['scores']['semantics']=1
    r=compare(a,b,fixture(),fixture())
    assert 'low_semantics' in r['phases']['development_review']['arbitration'][0]['reasons']
    assert r['automatic_approvals']==0

def test_calibration_separate_from_development():
    template=fixture();template['items'][0]['phase']='calibration'
    a,b=filled('A'),filled('B')
    for f in (a,b):f['items'][0]['phase']='calibration'
    r=compare(a,b,template,template)
    assert r['phases']['calibration']['completed_pairs']==1
    assert r['phases']['development_review']['completed_pairs']==0

def test_insufficient_context_cannot_have_numeric_scores():
    a=filled('A');a['items'][0]['context_sufficient']=False
    with pytest.raises(ValueError,match='insufficient_context_scored'):validate(a,fixture())

def test_ai_human_is_not_independent_human_agreement():
    a,b=filled('Great Attractor'),filled('Auditor');a['reviewer']['role']='ai'
    r=compare(a,b,fixture(),fixture())
    assert r['review_mode']=='ai_assisted_human_audit'
    assert r['independent_human_agreement'] is False
    assert r['phases']['development_review']['scales']['semantics']['weighted_kappa'] is None
    assert r['automatic_approvals']==0

def test_unknown_roles_cannot_claim_human_agreement():
    a,b=filled('A'),filled('B');del a['reviewer']['role']
    assert compare(a,b,fixture(),fixture())['status']=='not_ready'
