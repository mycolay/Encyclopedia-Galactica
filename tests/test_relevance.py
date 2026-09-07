from modules.lexicography.relevance import evidence_key,select_derivations

def record():
    return dict(work_id=1,artifact_sha256='a',term_orig='robot',window_sha256='b')

def decision():
    return dict(decision='include',reviewer_role='human',reviewer='fixture',rationale='fixture',reviewed_at='2026-09-07')

def test_no_decision_means_no_generation():
    assert select_derivations([record()],{})[0]==[]

def test_matching_review_allows_candidate():
    r=record();assert select_derivations([r],{evidence_key(r):decision()})[0]==[r]

def test_changed_context_invalidates_review():
    r=record();d={evidence_key(r):decision()};r['window_sha256']='changed'
    assert select_derivations([r],d)[0]==[]

def test_model_label_cannot_replace_human_review():
    r=record();d=decision();d['reviewer_role']='model'
    assert select_derivations([r],{evidence_key(r):d})[0]==[]

def test_exclusion_and_missing_rationale_do_not_pass():
    r=record();d=decision();d['decision']='exclude'
    assert select_derivations([r],{evidence_key(r):d})[0]==[]
    d=decision();d['rationale']=''
    assert select_derivations([r],{evidence_key(r):d})[0]==[]
