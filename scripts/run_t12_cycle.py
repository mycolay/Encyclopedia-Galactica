import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from core.db import DatabaseManager
from modules.corpus.manager import CorpusManager
from modules.autoresearch.llm_client import LocalLLMClient
from modules.autoresearch.loop import AutoResearchRunner

def main():
    db = DatabaseManager()
    corpus_mgr = CorpusManager()
    llm_client = LocalLLMClient("qwen3.5:27b")
    
    runner = AutoResearchRunner(db=db, corpus_mgr=corpus_mgr, llm_client=llm_client)
    
    target = db.get_work_by_id(15) # The Time Machine
    print(f"Targeting work: {target['title_orig']} ({target['text_path']})", flush=True)
    
    res = runner.run_single_cycle(target_work=target)
    print("Cycle Result:", res, flush=True)

if __name__ == "__main__":
    main()
