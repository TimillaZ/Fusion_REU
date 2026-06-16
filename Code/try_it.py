# try_it.py
#
# This file just RUNS the engine on some examples so you can see it work.
# Run it from a terminal with:   python try_it.py
# (Make sure fusion_engine.py is in the same folder as this file.)

# Bring in the two things we built in the other file.
from fusion_engine import TierResult, fuse


# A little helper so each example prints nicely. Don't overthink it.
def show(title, edge, fog, mode):
    print("-" * 60)          # a divider line
    print(title)
    print("  edge said:", edge.text if not edge.failed else "(FAILED)")
    print("  fog  said:", fog.text if not fog.failed else "(FAILED)")
    print("  FUSED  ->", fuse(edge, fog, mode))


# EXAMPLE 1: sequential, both worked ("Where is my gate?")
show(
    "1) Sequential, both tiers worked:",
    edge=TierResult(text="Your gate is B12"),
    fog=TierResult(text="it's in Terminal 2, turn left at security, 400 meters ahead"),
    mode="sequential",
)

# EXAMPLE 2: parallel, both worked ("Is my bag near a charging port?")
show(
    "2) Parallel, both tiers worked:",
    edge=TierResult(text="Your bag is a black backpack"),
    fog=TierResult(text="a charging port is 20 meters to your left"),
    mode="parallel",
)

# EXAMPLE 3: fog failed (e.g. the fog server timed out)
show(
    "3) Fog tier failed:",
    edge=TierResult(text="Your gate is B12"),
    fog=TierResult(failed=True),          # no text, marked as failed
    mode="sequential",
)

# EXAMPLE 4: edge failed (couldn't read the personal profile)
show(
    "4) Edge tier failed:",
    edge=TierResult(failed=True),
    fog=TierResult(text="the charging port is 20 meters to your left"),
    mode="parallel",
)

# EXAMPLE 5: both failed
show(
    "5) Both tiers failed:",
    edge=TierResult(failed=True),
    fog=TierResult(failed=True),
    mode="parallel",
)

print("-" * 60)