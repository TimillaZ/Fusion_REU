# run_testset.py
#
# Run with:   python run_testset.py
#
# This loads your dataset (fusion_testset.json), runs every case through your
# fuse() engine, and gives you a SCORE: for how many cases did all the
# important facts survive the merge? That score is your first real evaluation
# number ("merge correctness" from the project plan).
#
# Plain Python. "json" is built in, nothing to install.

import json
from fusion_engine import TierResult, fuse   # your existing engine


# Load the dataset file into a Python list of dictionaries.
with open("fusion_testset.json", "r", encoding="utf-8") as f:
    cases = json.load(f)


# Helper: build a TierResult from the JSON fields for one tier.
def make_tier(answer_text, failed_flag):
    return TierResult(text=answer_text, failed=failed_flag)


# Helper: did every required fact show up in the fused sentence?
# We compare in lowercase so "B12" matches "b12", etc.
def all_facts_present(fused_sentence, required_facts):
    fused_lower = fused_sentence.lower()
    for fact in required_facts:
        if fact.lower() not in fused_lower:
            return False        # a required fact is missing -> this case fails
    return True                 # every required fact was found -> this case passes


correct = 0   # how many cases passed
total = len(cases)

for case in cases:
    # Build the two tier results from the dataset row.
    edge = make_tier(case["edge_answer"], case["edge_failed"])
    fog  = make_tier(case["fog_answer"],  case["fog_failed"])

    # Run YOUR engine.
    fused = fuse(edge, fog, case["mode"])

    # Score this case.
    passed = all_facts_present(fused, case["must_include"])
    if passed:
        correct += 1

    # Print it so you can read what happened.
    mark = "PASS" if passed else "FAIL"
    print("-" * 64)
    print(f"[{mark}] case {case['id']}: \"{case['query']}\"  (mode: {case['mode']})")
    print("   fused ->", fused)
    print("   needed ->", case["must_include"] if case["must_include"] else "(nothing required)")

print("=" * 64)
print(f"MERGE CORRECTNESS: {correct} / {total} cases passed "
      f"({100 * correct / total:.0f}%)")
print("=" * 64)