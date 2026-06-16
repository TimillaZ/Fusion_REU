# try_timeout.py
#
# Run this with:   python try_timeout.py
# It calls the tiers with a DEADLINE and feeds the results into your fuse().
# This time, failure is NOT typed by hand — it happens because fog is too slow.

from tiers import edge_tier, fog_tier, run_tier   # the new stuff
from fusion_engine import fuse                     # your existing engine

# Our deadline: each tier gets at most this many seconds to answer.
DEADLINE = 0.5   # half a second


print("=" * 60)
print("CASE A: both tiers are fast (answer within the deadline)")
# edge takes 0.1s, fog takes 0.2s -- both under the 0.5s deadline.
edge = run_tier(edge_tier, delay=0.1, timeout_seconds=DEADLINE)
fog  = run_tier(fog_tier,  delay=0.2, timeout_seconds=DEADLINE)
print("  edge failed? ", edge.failed)
print("  fog  failed? ", fog.failed)
print("  FUSED ->", fuse(edge, fog, mode="sequential"))

print("=" * 60)
print("CASE B: fog is too slow (takes 2s, deadline is 0.5s) -> it times out")
# edge is quick, but fog takes 2 seconds -- it will blow the deadline and fail.
edge = run_tier(edge_tier, delay=0.1, timeout_seconds=DEADLINE)
fog  = run_tier(fog_tier,  delay=0.2, timeout_seconds=DEADLINE)
print("  edge failed? ", edge.failed)
print("  fog  failed? ", fog.failed)
print("  FUSED ->", fuse(edge, fog, mode="sequential"))

print("=" * 60)