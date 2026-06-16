# try_llm.py
#
# Run with:   python try_llm.py
#
# Shows the TEMPLATE merge and the LLM merge side by side, so you can see the
# difference. If Ollama isn't running, the LLM column falls back to the
# template (with a note) instead of crashing.

from fusion_engine import TierResult, fuse
from llm_fuse import llm_fuse


def compare(title, edge, fog, mode):
    print("=" * 64)
    print(title, f"(mode: {mode})")
    print("  TEMPLATE ->", fuse(edge, fog, mode))
    print("  LLM      ->", llm_fuse(edge, fog, mode))


# 1) Both answers present -> the LLM should write one smoother sentence.
compare(
    "1) Where is my gate?",
    edge=TierResult(text="Your gate is B12"),
    fog=TierResult(text="it's in Terminal 2, turn left at security, 400 meters ahead"),
    mode="sequential",
)

# 2) Parallel, both present.
compare(
    "2) Is my bag near a charging port?",
    edge=TierResult(text="Your bag is a black backpack"),
    fog=TierResult(text="a charging port is 20 meters to your left"),
    mode="parallel",
)

# 3) Fog failed -> MAMMQA abstention: no model call, safe fallback used.
compare(
    "3) Fog failed (abstention)",
    edge=TierResult(text="Your gate is C9"),
    fog=TierResult(failed=True),
    mode="sequential",
)

print("=" * 64)