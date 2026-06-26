# compare_approaches_repeated.py
#
# Run with:   python compare_approaches_repeated.py
#        or:  python compare_approaches_repeated.py 50      (50 repeats)
#
# Why this file exists
# --------------------
# compare_approaches.py runs the dataset through each approach ONCE. That is
# fine for the template, which is deterministic: it produces the exact same
# sentence every time, so one run tells you everything.
#
# The LLM is different. It is STOCHASTIC -- ask it the same thing twice and the
# wording can change ("400 meters" -> "four hundred meters", reordering, etc.).
# Because merge-correctness checks for exact strings, the SAME case can pass on
# one run and fail on the next. A single run is therefore not a fair measure of
# the LLM.
#
# So here we run each approach over the whole dataset MANY times and report:
#   - the average score, plus how much it varies (stdev, min, max)
#   - a per-case reliability rate: of N runs, how often did this case pass?
#   - timing, so you also get a feel for cost per call
#
# This turns "the LLM scored 75% that one time" into "the LLM scored
# 78% +/- 6% over 20 runs, and case 1 is the flaky one (passes 12/20)."
#
# Plain Python. "statistics" and "json" are built in -- nothing to install.

import sys
import json
import time
import statistics

from fusion_engine import TierResult, fuse   # Approach 1: template
from llm_fuse import llm_fuse                 # Approach 2: LLM synthesis
from graph_fuse import graph_fuse        # Approach 3: graph fusion

# How many times to run each approach over the full dataset.
# You can override it from the command line: python compare_approaches_repeated.py 50
DEFAULT_REPEATS = 20
REPEATS = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPEATS

# The approaches to compare, by name. Each name points to a function with the
# same shape: fuse(edge, fog, mode) -> str.
APPROACHES = {
    "template": fuse,
    "llm": llm_fuse,
    "graph": graph_fuse,
}

# Approaches whose output never changes between runs. We still run them, but we
# only run them ONCE (repeating a deterministic function just wastes time) and
# report that single result as if it were every run.
DETERMINISTIC = {"template"}


# Load the dataset once.
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


# ---------------------------------------------------------------------------
# Run the WHOLE dataset once. Return:
#   score        -> 0..100 for this pass
#   per_case     -> dict {case_id: True/False} did this case pass this pass?
#   elapsed      -> seconds the whole pass took
# ---------------------------------------------------------------------------
def run_once(fuse_function):
    correct = 0
    per_case = {}
    start = time.perf_counter()
    for case in cases:
        edge = make_tier(case["edge_answer"], case["edge_failed"])
        fog  = make_tier(case["fog_answer"],  case["fog_failed"])

        fused = fuse_function(edge, fog, case["mode"])
        passed = all_facts_present(fused, case["must_include"])

        per_case[case["id"]] = passed
        if passed:
            correct += 1

    elapsed = time.perf_counter() - start
    score = 100 * correct / len(cases)
    return score, per_case, elapsed


# ---------------------------------------------------------------------------
# Run one approach `repeats` times and summarise the spread.
# ---------------------------------------------------------------------------
def score_approach(name, fuse_function, repeats):
    # Deterministic approaches give the same answer every time, so one run is
    # enough -- we just label it as covering all the repeats.
    effective_repeats = 1 if name in DETERMINISTIC else repeats

    print("#" * 64)
    note = "  (deterministic: ran once)" if name in DETERMINISTIC else ""
    print(f"APPROACH: {name}   x{repeats} runs{note}")

    scores = []                                   # one score per run
    pass_counts = {case["id"]: 0 for case in cases}  # how often each case passed
    times = []                                    # seconds per run

    for run_index in range(effective_repeats):
        score, per_case, elapsed = run_once(fuse_function)
        scores.append(score)
        times.append(elapsed)
        for case_id, passed in per_case.items():
            if passed:
                pass_counts[case_id] += 1
        # a light progress line so long LLM runs don't look frozen
        print(f"  run {run_index + 1:>3}/{effective_repeats}: "
              f"{score:5.1f}%   ({elapsed:.2f}s)")

    # If we only ran once but were asked for many repeats, treat that single
    # result as representative of all of them for the per-case reliability.
    shown_repeats = repeats
    if name in DETERMINISTIC:
        scores = scores * repeats
        for case_id in pass_counts:
            pass_counts[case_id] *= repeats

    mean_score = statistics.mean(scores)
    stdev_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
    min_score = min(scores)
    max_score = max(scores)
    mean_time = statistics.mean(times)

    print("  " + "-" * 60)
    print(f"  score over {shown_repeats} runs: "
          f"mean {mean_score:.1f}%  stdev {stdev_score:.1f}  "
          f"min {min_score:.0f}%  max {max_score:.0f}%")
    print(f"  time: {mean_time:.2f}s per full pass "
          f"({mean_time / len(cases):.3f}s per case)")

    # Per-case reliability: which cases are rock-solid and which are flaky?
    print("  per-case reliability (passes / runs):")
    for case in cases:
        cid = case["id"]
        passed = pass_counts[cid]
        rate = 100 * passed / shown_repeats
        flag = "" if rate == 100 else "  <-- flaky" if rate > 0 else "  <-- always fails"
        print(f"    case {cid}: {passed:>3}/{shown_repeats}  ({rate:5.1f}%){flag}")

    return {
        "mean": mean_score,
        "stdev": stdev_score,
        "min": min_score,
        "max": max_score,
        "mean_time": mean_time,
    }


# Run every approach and remember each summary.
results = {}
for name, fn in APPROACHES.items():
    results[name] = score_approach(name, fn, REPEATS)

# Final comparison table.
print("=" * 64)
print(f"SUMMARY  (metric: merge correctness, {REPEATS} runs each)")
print(f"  {'approach':>10} | {'mean':>6} | {'stdev':>6} | {'min':>4} | {'max':>4} | {'s/pass':>7}")
print("  " + "-" * 56)
for name, r in results.items():
    print(f"  {name:>10} | {r['mean']:5.1f}% | {r['stdev']:6.1f} | "
          f"{r['min']:3.0f}% | {r['max']:3.0f}% | {r['mean_time']:6.2f}s")
print("=" * 64)