# fusion_engine.py
#
# This is the heart of your project, kept as simple as possible.
# It does ONE job: take two text answers (one personal "edge" answer and one
# environmental "fog" answer) and join them into a single sentence.
#
# There is NO machine learning here. No model. No Raspberry Pi. No internet.
# It is plain Python. You can read every line.

# "dataclass" is a built-in Python helper that lets us make a tiny container
# for related pieces of data without writing much code. It ships with Python,
# so there is nothing to install.
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# PART 1: a small container that describes ONE tier's answer.
# ---------------------------------------------------------------------------
# Think of this as a labeled box. Each tier (edge or fog) hands you a box that
# says: here is my answer text, and here is whether I failed.
@dataclass
class TierResult:
    text: Optional[str] = None   # the answer sentence. None means "no answer".
    failed: bool = False         # True if this tier timed out or errored.

    def is_usable(self) -> bool:
        return (not self.failed) and (self.text is not None)


# ---------------------------------------------------------------------------
# PART 2: a helper so we never get ugly double punctuation like "B12.."
# ---------------------------------------------------------------------------
# Edge or fog might hand us a sentence that already ends in a period. When we
# glue sentences together we don't want "...B12. — Terminal 2." with stray dots.
# This function removes a trailing period/space so we can add our own cleanly.
def tidy(text: str) -> str:
    return text.strip().rstrip(".").strip()


# ---------------------------------------------------------------------------
# PART 3: the fusion function itself — the thing you were asked to build.
# ---------------------------------------------------------------------------
# It takes:
#   edge  -> a TierResult (the user's PERSONAL answer, e.g. "Your gate is B12")
#   fog   -> a TierResult (the ENVIRONMENTAL answer, e.g. "Terminal 2, 400m ahead")
#   mode  -> the string "parallel" or "sequential"
# It returns ONE sentence (a string) for the blind user to hear.
def fuse(edge: TierResult, fog: TierResult, mode: str) -> str:

    # CASE 1: both tiers gave a usable answer. This is the normal "happy path".
    if edge.is_usable() and fog.is_usable():
        e = tidy(edge.text)   # cleaned-up edge sentence
        f = tidy(fog.text)    # cleaned-up fog sentence

        if mode == "parallel":
            # Parallel = the two facts are independent, so we list them.
            return f"{e}, and {f}."
        else:
            # Sequential = the fog answer follows from the edge answer,
            # so we connect them with a dash to read as one flowing thought.
            return f"{e} — {f}."

    # CASE 2: only EDGE worked (fog failed or was empty).
    # We still give the user their personal info, and we honestly say we
    # could not get the location. (Partial truth beats silence.)
    if edge.is_usable():
        return f"{tidy(edge.text)}. I couldn't find the location right now."

    # CASE 3: only FOG worked (edge failed or was empty).
    # We give the environmental info and admit we couldn't reach personal data.
    if fog.is_usable():
        return f"{tidy(fog.text)}. I couldn't access your personal data right now."

    # CASE 4: nothing worked. We fail gracefully with a calm apology instead
    # of crashing or making something up.
    return "I'm sorry, I couldn't answer that right now. Please try again."