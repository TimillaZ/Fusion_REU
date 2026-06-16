# tiers.py
#
# Goal of this file: make "failure" happen on its own.
# Until now you set failed=True by hand. In a real system, a tier fails
# because it is too SLOW and runs out of time. That is a "timeout".
#
# Still plain Python. Nothing to install. Works on Windows.

import time                                   # lets us pause / measure time
from concurrent.futures import ThreadPoolExecutor, TimeoutError  # the timeout tool
from fusion_engine import TierResult          # reuse the box you already have


# ---------------------------------------------------------------------------
# PART 1: two PRETEND tiers. Each is just a function that waits, then answers.
# ---------------------------------------------------------------------------
# The "delay" argument is how many seconds this tier takes to think.
# We use time.sleep() to fake "doing work". Later, real work goes here instead.

def edge_tier(delay: float) -> str:
    time.sleep(delay)                 # pretend the edge is thinking
    return "Your gate is B12"         # then it returns its personal answer


def fog_tier(delay: float) -> str:
    time.sleep(delay)                 # pretend the fog is thinking
    return "it's in Terminal 2, turn left at security, 400 meters ahead"


# ---------------------------------------------------------------------------
# PART 2: the timeout wrapper. This is the new important piece.
# ---------------------------------------------------------------------------
# It runs a tier function, but only WAITS for it up to "timeout_seconds".
# - If the tier finishes in time, we wrap its text in a good TierResult.
# - If the tier is too slow, we catch the timeout and return a FAILED TierResult.
#   Your fuse() already knows what to do with a failed tier, so nothing else changes.

def run_tier(tier_function, delay: float, timeout_seconds: float) -> TierResult:
    # ThreadPoolExecutor lets us start the work and walk away with a deadline.
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(tier_function, delay)   # start the tier running
        try:
            answer = future.result(timeout=timeout_seconds)  # wait, but not forever
            return TierResult(text=answer)                    # got it in time -> good
        except TimeoutError:
            return TierResult(failed=True)                    # too slow -> failed