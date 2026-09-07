"""Prepare development review forms; does not manufacture ratings or blinding."""
import argparse
import hashlib
import json
from pathlib import Path
import random


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True)
    cards=json.loads(Path('docs/SCI_FI_LEXICON.json').read_text(encoding='utf-8'))['cards']
    items=[];mapping={}
    for card in cards:
        for proposal in card['proposals']:
            ident=hashlib.sha256(('review.v1:'+str(proposal['id'])).encode()).hexdigest()[:16]
            mapping[ident]=dict(proposal_id=proposal['id'],work_id=card['work_id'])
            items.append(dict(id=ident,term=card['term'],title=card['title'],variant=proposal['variant'],
                rationale=proposal['rationale'],contexts=[dict(quote=x['quote'],byte_start=x['byte_start'],
                byte_len=x['byte_len'],source_sha256=x['artifact_sha256']) for x in card['attestations']],
                context_sufficient=None,relevance=None,relevance_reason='',
                scores=dict(semantics=None,naturalness=None,word_formation=None,style=None),
                na_reasons={},comment='',recognized_provenance=None))
    ordered=sorted(items,key=lambda x:x['id']);random.Random(901).shuffle(ordered)
    calibration={x['id'] for x in ordered[:10]}
    for x in items:x['phase']='calibration' if x['id'] in calibration else 'development_review'
    for number in [1,2]:
        shuffled=list(items);random.Random(901+number).shuffle(shuffled)
        folder=args.output/('reviewer-'+str(number));folder.mkdir()
        payload=dict(status='unfilled_preparation',reviewer=dict(name='Great Attractor' if number==1 else None,
            role='ai' if number==1 else 'human',source_language_competence=None,
            ukrainian_competence=None,philological_experience=None,conflicts=None),
            blindness='Open AI-assisted human audit; not two independent human reviewers or a held-out blind study.',items=shuffled)
        (folder/'ratings.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.output/'coordinator-key.json').write_text(json.dumps(mapping,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(unique_proposals=len(items),calibration=len(calibration),development=len(items)-len(calibration),human_ratings=0)))


if __name__=='__main__':main()
