import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules.autoresearch.llm_client import LocalLLMClient
from modules.corpus.witness import build_witness, render_quote
from modules.lexicography.grinchenko_engine import GrinchenkoEngine

def main():
    client = LocalLLMClient("qwen3.5:27b")
    path = "K:/scifi_library/authors/h-g-wells/the-time-machine/full_text.md"
    w = build_witness(path, "Time Machine", occurrence_index=3)
    print("Witness:", w, flush=True)
    quote = render_quote(w, path, "Time Machine")
    print("Quote:", quote, flush=True)
    print("Calling Ollama derive_ukrainian_neologism...", flush=True)
    deriv = client.derive_ukrainian_neologism("Time Machine", quote, "The Time Machine", "H.G. Wells")
    print("Deriv result:", deriv.get("json"), flush=True)
    
    proposed_ukr = deriv.get("json", {}).get("proposed_ukr_term", "")
    note = deriv.get("json", {}).get("stylistic_note", "")
    model = deriv.get("json", {}).get("derivation_model", "")
    eval_res = GrinchenkoEngine.evaluate_ukrainian_neologism(proposed_ukr, f"{note} {model}")
    print("Evaluation:", eval_res, flush=True)

if __name__ == "__main__":
    main()
