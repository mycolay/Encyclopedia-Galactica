"""Seal an existing export or verify a package using a separately retained anchor."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from modules.audit.exometric import seal_run, verify_bundle

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['seal','verify'])
    parser.add_argument('--run',type=Path)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--anchor',type=Path,required=True)
    args=parser.parse_args()
    if args.mode=='seal' and args.run is None:
        parser.error('--run required for seal')
    try:
        result=seal_run(args.run,args.bundle,args.anchor) if args.mode=='seal' else verify_bundle(args.bundle,args.anchor)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr)
        sys.exit(2)
