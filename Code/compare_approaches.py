# compare_approaches.py
#
# Run with:   python compare_approaches.py
#
# This runs your dataset through EACH fusion approach and scores "merge
# correctness" for each, so you can compare them with real numbers.
# This is the first column of your comparison table (approaches x metrics).

import json
from fusion_engine import TierResult, fuse        # Approach 1: template
from llm_fuse import llm_fuse                       # Approach 2: LLM synthesis
from graph_fuse import graph_fuse        # Approach 3: graph fusion
import time 


# The approaches we want to compare, by name.
# Each name points to a function with the same shape: fuse(edge, fog, mode).
APPROACHES = {
    "template": fuse,
    #"llm": llm_fuse,
    "graph": graph_fuse,
}


# Load the dataset.
with open("fusion_testset.json", "r", encoding="utf-8") as f:
    cases = json.load(f)


def make_tier(answer_text, failed_flag):
    return TierResult(text=answer_text, failed=failed_flag)


def all_facts_present(fused_sentence, required_facts):
    fused_lower = fused_sentence.lower()
    for fact in required_facts:
        if fact.lower() not in fused_lower:
            return False
    return True


# Run one approach over the whole dataset and return its score (0..100).
def score_approach(name, fuse_function):
    correct = 0
    print("#" * 64)
    print(f"APPROACH: {name}")
    for case in cases:
        start_time = time.time()
        edge = make_tier(case["edge_answer"], case["edge_failed"])
        fog  = make_tier(case["fog_answer"],  case["fog_failed"])

        fused = fuse_function(edge, fog, case["mode"])   # run THIS approach
        passed = all_facts_present(fused, case["must_include"])
        if passed:
            correct += 1

        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] case {case['id']}: {fused}")
        print(time.time() - start_time)

    score = 100 * correct / len(cases)
    print(f"  --> {name}: {correct}/{len(cases)} ({score:.0f}%)")
    return score


# Run every approach and remember each score.
results = {}
for name, fn in APPROACHES.items():
    results[name] = score_approach(name, fn)

# Print the summary table -- this is the start of your real result.
print("=" * 64)
print("SUMMARY  (metric: merge correctness)")
for name, score in results.items():
    print(f"  {name:>10} : {score:.0f}%")
print("=" * 64)