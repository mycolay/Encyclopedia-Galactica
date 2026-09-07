"""Replay recorded outputs against source checks and a non-gold editorial fixture."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from modules.lexicography.entity_checks import check_entity, locate
from modules.audit.exometric import write_json, sha


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    records=json.loads((ROOT/'docs/WORLD_PILOT_RESULTS.json').read_text(encoding='utf-8'))
    reference=json.loads((ROOT/'docs/WORLD_REFERENCE_DRAFT_V1.json').read_text(encoding='utf-8'))
    source=ROOT/'.benchmarks/world-step07-001/source.txt'
    if sha(source)!=reference['source_sha256']:raise ValueError('source_drift')
    data=source.read_bytes();scenes={x['scene']['id']:x['scene'] for x in records}
    for s in scenes.values():
        if data[s['byte_start']:s['byte_start']+s['byte_len']]!=s['text'].encode():raise ValueError('scene_drift')
    for item in reference['entities']:
        check=check_entity(dict(item,epistemic='explicit'),scenes[item['scene']])
        if check['issues']:raise ValueError('invalid_reference_evidence:'+str(check['issues']))
    expected={(x['scene'],x['name']):x for x in reference['entities']}
    exclusions={(x['scene'],x['name']):x for x in reference['exclusions']}
    rows=[]
    for record in records:
        scene=record['scene']
        for arm in ['original_only','translation_assisted']:
            for previous in ['accepted','rejected']:
                for item in record[arm][previous]:
                    check=check_entity(item,scene);key=(scene['id'],item['name'])
                    ref=expected.get(key);excluded=exclusions.get(key)
                    decision='unmapped_review_required'
                    if ref:decision='category_matches_draft' if item['kind']==ref['kind'] else 'category_conflicts_with_draft'
                    if excluded:decision='excluded_by_draft_scope'
                    rows.append(dict(scene=scene['id'],arm=arm,original=item,previous_quote_status=previous,
                        checks=check,reference_decision=decision,reference=ref or excluded,
                        publication='pending_human_review'))
    summary=dict(candidates=len(rows),source_held=sum(bool(x['checks']['issues']) for x in rows),
        whitespace_recovered=sum(x['previous_quote_status']=='rejected' and x['checks']['evidence'] is not None for x in rows),
        draft_excluded=sum(x['reference_decision']=='excluded_by_draft_scope' for x in rows),
        semantic_approved=0,llm_calls=0)
    write_json(args.output,dict(reference_status=reference['status'],summary=summary,rows=rows,
        reference_sha256=sha(ROOT/'docs/WORLD_REFERENCE_DRAFT_V1.json'),input_sha256=sha(ROOT/'docs/WORLD_PILOT_RESULTS.json')))
    print(json.dumps(summary))


if __name__=='__main__':main()
