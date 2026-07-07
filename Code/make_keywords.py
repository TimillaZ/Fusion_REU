# make_keywords.py
#
# Run with:   python make_keywords.py                (report only)
#        or:  python make_keywords.py --write        (also saves fusion_testset_auto.json)
#
# WHY THIS EXISTS (meeting note, week 5):
#   "Find a way to get keywords like the must_include in the JSON file
#    so we don't have to get those by hand."
#
# Until now every test case listed its required facts ("must_include") by
# hand. That doesn't scale: 8 cases is fine, 80 is not. This script derives
# the keywords AUTOMATICALLY from the tier answers themselves, using the
# same idea as the graph approach: the facts that must survive a merge are
# the ANCHORS of each answer.
#
# WHAT COUNTS AS A REQUIRED FACT
# ------------------------------
#   1. CODES        tokens containing a digit            -> B12, A4, C9
#   2. PLACE PHRASES a word + number pair                -> Terminal 2, row 4, counter 3
#   3. BARE NUMBERS distances / counts                   -> 400, 20, 50, 10
#   4. SUBJECT NOUNS the thing the answer is about       -> backpack, elevator, restroom
#      * if an answer already carries a code ("Your gate is B12"), the code
#        identifies the fact, so the generic noun ("gate") is NOT required.
#        This mirrors the node-merge rule in graph_fuse.py.
#   5. Failed tiers contribute nothing (their facts cannot be required).
#
# Plain Python + regex; no installs. If spaCy is present, graph_fuse's
# entity extraction can replace the regex heuristics for extra robustness.

import re
import sys
import json

# Words that never identify anything by themselves.
DETERMINERS = {"the", "a", "an", "your", "my", "his", "her", "their", "its"}
SPATIAL     = {"left", "right", "ahead", "behind", "straight", "forward",
               "north", "south", "east", "west", "past", "opposite",
               "near", "nearest", "closest", "next"}
UNITS       = {"meters", "metres", "meter", "metre", "steps", "step"}
PRONOUNS    = {"it", "that", "this", "they", "he", "she"}
GENERIC     = DETERMINERS | SPATIAL | UNITS | PRONOUNS | {
    "is", "are", "in", "at", "on", "to", "and", "turn", "of", "for", "with",
}

CODE   = re.compile(r"\b[A-Za-z]*\d[A-Za-z\d]*\b")           # B12, A4, 400
PHRASE = re.compile(r"\b([A-Za-z][A-Za-z-]+)\s+(\d+)\b")      # Terminal 2, row 4
SPLIT  = re.compile(r"\b(?:is|are)\b", re.IGNORECASE)


def _clean_words(text):
    return re.findall(r"[A-Za-z][A-Za-z-]*|\d+", text)


def keywords_for_answer(text):
    """Required facts from ONE tier answer (see rules in the header)."""
    if not text:
        return []
    kws, seen = [], set()

    def add(kw):
        low = kw.lower()
        if low not in seen and low not in GENERIC:
            seen.add(low)
            kws.append(kw)

    # 2. place phrases first (Terminal 2, row 4, counter 3) so their numbers
    #    are not double-counted as bare numbers below.
    used_numbers = set()
    for word, num in PHRASE.findall(text):
        if word.lower() in SPATIAL | UNITS | GENERIC:
            continue                       # "ahead 200" is not a place phrase
        add(f"{word} {num}")
        used_numbers.add(num)

    # 1 + 3. codes and bare numbers.
    has_code = False
    for tok in CODE.findall(text):
        if tok.isdigit():
            if tok not in used_numbers:
                add(tok)
        else:
            has_code = True
            add(tok)                       # B12, A4, C9

    # 4. subject noun: the thing this answer is about.
    parts = SPLIT.split(text, maxsplit=1)
    if len(parts) == 2:
        subject, predicate = parts
        subj_words = [w for w in _clean_words(subject)
                      if w.lower() not in GENERIC and not w.isdigit()]
        if subj_words and subj_words[-1].lower() not in PRONOUNS:
            if not (has_code or used_numbers):
                # no anchor yet -> the noun phrase itself is the identifying
                # fact; keep the full phrase ("charging port", not just "port")
                add(" ".join(subj_words))  # charging port, restroom, elevator
            # capitalised words in the subject are entities either way (Delta)
        for w in subj_words:
            if w[0].isupper() and subject.strip().split()[0] != w:
                add(w)                     # Delta, Gate A4's "Gate" skipped by GENERIC? no: add entity
        # possessive pattern "Your bag is a black backpack": if the answer has
        # no code/number, the PREDICATE's last content word is the fact.
        pred_words = [w for w in _clean_words(predicate)
                      if w.lower() not in GENERIC and not w.isdigit()]
        if pred_words and not (has_code or used_numbers):
            add(pred_words[-1])            # backpack
    # capitalised mid-sentence entities anywhere (Delta, Terminal already phrased)
    words = text.split()
    for i, w in enumerate(words):
        wc = re.sub(r"[^A-Za-z0-9-]", "", w)
        if i > 0 and wc[:1].isupper() and wc.lower() not in GENERIC and not CODE.search(wc):
            add(wc)
    return kws


def keywords_for_case(case):
    """Union of required facts from every usable tier, order kept."""
    kws, seen = [], set()
    for answer_key, failed_key in (("edge_answer", "edge_failed"),
                                   ("fog_answer", "fog_failed")):
        if case[failed_key]:
            continue
        for kw in keywords_for_answer(case[answer_key]):
            low = kw.lower()
            if low not in seen:
                seen.add(low)
                kws.append(kw)
    return kws


if __name__ == "__main__":
    with open("fusion_testset.json", "r", encoding="utf-8") as f:
        cases = json.load(f)

    agree = 0
    for case in cases:
        auto = keywords_for_case(case)
        hand = case["must_include"]
        auto_blob = " ".join(auto).lower()
        covered = all(h.lower() in auto_blob for h in hand)
        agree += covered
        mark = "OK " if covered else "GAP"
        print(f"[{mark}] case {case['id']}")
        print(f"      hand: {hand}")
        print(f"      auto: {auto}")

    print("=" * 60)
    print(f"auto keywords cover the hand-made ones in {agree}/{len(cases)} cases")

    if "--write" in sys.argv:
        for case in cases:
            case["must_include"] = keywords_for_case(case)
        with open("fusion_testset_auto.json", "w", encoding="utf-8") as f:
            json.dump(cases, f, indent=2, ensure_ascii=False)
        print("wrote fusion_testset_auto.json (auto-generated must_include)")