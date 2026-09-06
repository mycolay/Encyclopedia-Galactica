import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules.autoresearch.llm_client import LocalLLMClient

def main():
    client = LocalLLMClient("qwen3.5:27b")
    text = (
        "The Time Traveller was expounding a recondite matter to us. "
        "His grey eyes shone and twinkled, and his usually pale face was flushed and animated. "
        "The fire burnt brightly, and the soft radiance of the incandescent lights in the lilies of silver "
        "caught the bubbles that flashed and passed in our glasses. 'You must follow me carefully. A mark space "
        "is only a frame of reference. Scientific people know very well that Time is only a kind of Space. "
        "Here is a popular scientific diagram, a weather chart. And this other is the Time Machine.'"
    )
    cands = client.propose_candidates(text, "The Time Machine", "H.G. Wells")
    print("Candidates:", cands)

if __name__ == "__main__":
    main()
