"""Validate independent review forms and compute descriptive ordinal agreement."""
SCALES = ('semantics', 'naturalness', 'word_formation', 'style')
EDITABLE = {'context_sufficient', 'relevance', 'relevance_reason', 'scores',
            'na_reasons', 'comment', 'recognized_provenance'}


def agreement(pairs):
    n = len(pairs)
    if not n:
        return dict(n=0, exact=None, within_one=None, weighted_kappa=None,
                    kappa_reason='no_pairs', contingency=[[0]*4 for _ in range(4)])
    table = [[0]*4 for _ in range(4)]
    for a,b in pairs:
        if type(a) is not int or type(b) is not int or not 0<=a<=3 or not 0<=b<=3:
            raise ValueError('invalid_score_pair')
        table[a][b] += 1
    rows=[sum(row) for row in table]; cols=[sum(row[j] for row in table) for j in range(4)]
    observed=sum(abs(a-b) for a,b in pairs)/n
    expected=sum(rows[a]*cols[b]*abs(a-b) for a in range(4) for b in range(4))/(n*n)
    return dict(n=n, exact=sum(a==b for a,b in pairs)/n,
        within_one=sum(abs(a-b)<=1 for a,b in pairs)/n,
        weighted_kappa=1-observed/expected if expected else None,
        kappa_reason=None if expected else 'degenerate_marginals',contingency=table)


def index(form):
    items=form.get('items')
    if not isinstance(items,list) or any(not isinstance(x,dict) or not isinstance(x.get('id'),str) for x in items):
        raise ValueError('invalid_items')
    result={x['id']:x for x in items}
    if len(result)!=len(items):raise ValueError('duplicate_ids')
    return result


def validate(form, template):
    actual,original=index(form),index(template)
    if actual.keys()!=original.keys():raise ValueError('item_set_changed')
    complete=[]
    for ident,item in actual.items():
        frozen=lambda x:{k:v for k,v in x.items() if k not in EDITABLE}
        if frozen(item)!=frozen(original[ident]):raise ValueError('protected_content_changed:'+ident)
        if item.get('context_sufficient') is not None and type(item['context_sufficient']) is not bool:
            raise ValueError('invalid_context_flag')
        if item.get('recognized_provenance') is not None and type(item['recognized_provenance']) is not bool:
            raise ValueError('invalid_recognition_flag')
        if item.get('relevance') not in (None,'include','exclude','uncertain'):raise ValueError('invalid_relevance')
        scores=item.get('scores');reasons=item.get('na_reasons')
        if not isinstance(scores,dict) or set(scores)!=set(SCALES) or not isinstance(reasons,dict):
            raise ValueError('invalid_score_schema')
        if set(reasons)-set(SCALES):raise ValueError('unknown_na_scale')
        for scale,value in scores.items():
            if value is not None and (type(value) is not int or not 0<=value<=3):raise ValueError('invalid_score')
            if scale in reasons and (not isinstance(reasons[scale],str) or not reasons[scale].strip()):raise ValueError('invalid_na_reason')
            if value is not None and scale in reasons:raise ValueError('score_and_na_conflict')
            if item.get('context_sufficient') is False and value is not None:raise ValueError('insufficient_context_scored')
        for field in ('comment','relevance_reason'):
            if not isinstance(item.get(field),str):raise ValueError('invalid_text_field')
        done=(type(item.get('context_sufficient')) is bool and item.get('relevance') is not None
            and bool(item['relevance_reason'].strip()) and type(item.get('recognized_provenance')) is bool
            and all(scores[s] is not None or s in reasons for s in SCALES))
        if done:complete.append(ident)
    return actual,set(complete)


def compare(first,second,template_first,template_second):
    a,done_a=validate(first,template_first);b,done_b=validate(second,template_second)
    if a.keys()!=b.keys():raise ValueError('reviewer_item_sets_differ')
    for ident in a:
        if {k:v for k,v in a[ident].items() if k not in EDITABLE}!={k:v for k,v in b[ident].items() if k not in EDITABLE}:
            raise ValueError('reviewer_contents_differ')
    people=[f.get('reviewer',{}) for f in (first,second)]
    roles=[p.get('role') if isinstance(p,dict) else None for p in people]
    mode='ai_assisted_human_audit' if sorted(str(r) for r in roles)==['ai','human'] else 'two_human_review' if roles==['human','human'] else 'unconfirmed_roles'
    ready=all(isinstance(p,dict) and all(isinstance(p.get(k),str) and p[k].strip()
        for k in ('name','source_language_competence','ukrainian_competence','philological_experience','conflicts')) for p in people)
    if mode=='ai_assisted_human_audit':
        ready=all(isinstance(p.get('name'),str) and p['name'].strip() for p in people)
    if mode=='unconfirmed_roles':ready=False
    if ready and people[0]['name'].strip().casefold()==people[1]['name'].strip().casefold():
        raise ValueError('same_reviewer')
    # Metadata are declarations, not proof of identity or competence.
    paired=done_a & done_b if ready else set()
    phases={}
    for phase in ('calibration','development_review'):
        ids=sorted(i for i in paired if a[i]['phase']==phase)
        metrics={};arbitration=[]
        for scale in SCALES:
            pairs=[(a[i]['scores'][scale],b[i]['scores'][scale]) for i in ids
                   if a[i]['scores'][scale] is not None and b[i]['scores'][scale] is not None]
            metrics[scale]=dict(agreement(pairs),na_pairs=len(ids)-len(pairs))
            if mode!='two_human_review':
                metrics[scale]['weighted_kappa']=None
                metrics[scale]['kappa_reason']='not_two_human_reviewers'
        for i in ids:
            reasons=[]
            if a[i]['relevance']!=b[i]['relevance']:reasons.append('relevance_disagreement')
            if any(x['relevance']=='uncertain' or not x['context_sufficient'] for x in (a[i],b[i])):reasons.append('uncertain_or_insufficient_context')
            for scale in SCALES:
                x,y=a[i]['scores'][scale],b[i]['scores'][scale]
                if x is None or y is None:reasons.append('NA:'+scale)
                elif abs(x-y)>=2:reasons.append('large_difference:'+scale)
                if scale=='semantics' and any(v is not None and v<=1 for v in (x,y)):reasons.append('low_semantics')
            if reasons:arbitration.append(dict(id=i,reasons=reasons))
        phases[phase]=dict(completed_pairs=len(ids),scales=metrics,arbitration=arbitration)
    return dict(status=('assisted_audit_comparison' if mode=='ai_assisted_human_audit' else 'descriptive_development_results') if paired else 'not_ready',
        review_mode=mode,independent_human_agreement=mode=='two_human_review' and bool(paired),
        reviewer_metadata_complete=ready,completed_first=len(done_a),completed_second=len(done_b),
        phases=phases,automatic_approvals=0,
        limitation='No independent identity check, no held-out inference, no aggregate quality score; comments still require coordinator review.')
