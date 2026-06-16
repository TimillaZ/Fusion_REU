# try_parallel.py
#
# Run with:   python try_parallel.py
#
# Idea: edge and fog don't depend on each other (parallel mode), so they can
# run AT THE SAME TIME. The user then only waits for the SLOWER one, not both
# added together. This file shows the time difference, and still uses your fuse().
#
# Plain Python. Nothing to install. Works on Windows.

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from tiers import edge_tier, fog_tier, run_tier   # your pretend tiers + timeout helper
from fusion_engine import TierResult, fuse          # your existing engine


# ---------------------------------------------------------------------------
# Helper: collect ONE result from an already-started tier, respecting the
# overall deadline measured from "start".
# ---------------------------------------------------------------------------
def collect(future, deadline, start):
    elapsed = time.perf_counter() - start          # how long since we kicked things off
    remaining = max(0.0, deadline - elapsed)        # time left before the deadline
    try:
        return TierResult(text=future.result(timeout=remaining))  # got it in time
    except TimeoutError:
        return TierResult(failed=True)                            # ran out of time


# ---------------------------------------------------------------------------
# Run BOTH tiers at the same time, with one shared deadline for the pair.
# ---------------------------------------------------------------------------
def run_both(edge_delay, fog_delay, deadline):
    # max_workers=2 means two things can run side by side.
    with ThreadPoolExecutor(max_workers=2) as pool:
        start = time.perf_counter()                 # start the clock
        edge_future = pool.submit(edge_tier, edge_delay)  # kick off edge...
        fog_future  = pool.submit(fog_tier,  fog_delay)   # ...and fog immediately after
        # Both are now running together. We just gather their results.
        edge_result = collect(edge_future, deadline, start)
        fog_result  = collect(fog_future,  deadline, start)
        return edge_result, fog_result


DEADLINE = 0.5

print("=" * 60)
print("THE SLOW WAY: one tier, then the other (what we did before)")
start = time.perf_counter()
edge = run_tier(edge_tier, delay=0.1, timeout_seconds=DEADLINE)  # finish edge first...
fog  = run_tier(fog_tier,  delay=0.2, timeout_seconds=DEADLINE)  # ...then start fog
elapsed = time.perf_counter() - start
print(f"  took about {elapsed:.2f} seconds (0.1 + 0.2 added up)")
print("  FUSED ->", fuse(edge, fog, mode="parallel"))

print("=" * 60)
print("THE FAST WAY: both tiers at the same time")
start = time.perf_counter()
edge, fog = run_both(edge_delay=0.1, fog_delay=0.2, deadline=DEADLINE)
elapsed = time.perf_counter() - start
print(f"  took about {elapsed:.2f} seconds (only waited for the slower one)")
print("  FUSED ->", fuse(edge, fog, mode="parallel"))

print("=" * 60)
print("FAST WAY, but fog is too slow (2s) -> it still times out gracefully")
start = time.perf_counter()
edge, fog = run_both(edge_delay=0.1, fog_delay=2.0, deadline=DEADLINE)
elapsed = time.perf_counter() - start
print(f"  took about {elapsed:.2f} seconds (gave up on fog at the deadline)")
print("  FUSED ->", fuse(edge, fog, mode="parallel"))

print("=" * 60)