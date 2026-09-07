"""Context-bound editorial gate before spending tokens on Ukrainian derivation."""
import hashlib
import json


def evidence_key(record):
    values=[record['work_id'],record['artifact_sha256'],record['term_orig'].casefold(),record['window_sha256']]
    return hashlib.sha256(json.dumps(values,ensure_ascii=False).encode()).hexdigest()


def select_derivations(records, decisions, limit=16):
    selected, held = [], []
    for record in records:
        key=evidence_key(record);decision=decisions.get(key,{})
        approved=(decision.get('decision')=='include' and
                  decision.get('reviewer_role')=='human' and
                  all(isinstance(decision.get(k),str) and decision[k].strip()
                      for k in ['reviewer','rationale','reviewed_at']))
        if approved and len(selected)<limit:
            selected.append(record)
        else:
            held.append(dict(evidence_key=key,term=record['term_orig'],
                reason='approved_over_budget' if approved else 'relevance_review_required'))
    return selected,held
