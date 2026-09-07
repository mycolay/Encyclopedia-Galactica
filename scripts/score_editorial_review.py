"""Read-only comparison; preserve submitted forms and reference templates."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from modules.lexicography.review_scores import compare
from modules.audit.exometric import sha,write_json

def main():
    parser=argparse.ArgumentParser()
    for name in ('first','second','template-first','template-second','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    paths=[args.first,args.second,args.template_first,args.template_second]
    result=compare(*(json.loads(p.read_text(encoding='utf-8')) for p in paths))
    result['input_sha256']=[sha(p) for p in paths]
    write_json(args.output,result)
    print(json.dumps(dict(status=result['status'],completed_first=result['completed_first'],completed_second=result['completed_second'])))

if __name__=='__main__':main()
