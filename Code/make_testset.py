# make_testset.py
#
# Run with:   python make_testset.py
#
# WHAT THIS DOES
# --------------
# Builds fusion_testset.json with 60 cases in the SAME format as before:
#   { id, query, mode, edge_answer, fog_answer, edge_failed, fog_failed, must_include }
#
# Your original 8 cases are kept unchanged as cases 1-8, so all your old
# results stay comparable. Cases 9-60 are new and cover:
#   - more sequential cases (fog gives directions to the personal fact)
#   - more parallel cases (personal item + independent nearby thing)
#   - node-merge cases (fog restates the edge's code -> tests de-duplication)
#   - CONTRADICTION cases (edge and fog disagree -> the week-7 hard cases)
#   - more failure cases (edge down, fog down, both down)
#
# The must_include keywords are derived automatically with the same rules
# used for your current file (codes like B12, place phrases like "Terminal 2",
# distances, subject nouns, capitalized names). No hand labeling.

import json
import re

# ---------------------------------------------------------------------------
# Keyword extraction (same rules that produced your current must_include)
# ---------------------------------------------------------------------------
DETERMINERS = {"the", "a", "an", "your", "my", "his", "her", "their", "its"}
SPATIAL     = {"left", "right", "ahead", "behind", "straight", "forward",
               "north", "south", "east", "west", "past", "opposite",
               "near", "nearest", "closest", "next", "downstairs", "upstairs"}
UNITS       = {"meters", "metres", "meter", "metre", "steps", "step", "minutes", "minute"}
PRONOUNS    = {"it", "that", "this", "they", "he", "she"}
GENERIC     = DETERMINERS | SPATIAL | UNITS | PRONOUNS | {
    "is", "are", "in", "at", "on", "to", "and", "turn", "of", "for", "with",
    "from", "by", "up", "down",
}

CODE   = re.compile(r"\b[A-Za-z]*\d[A-Za-z\d]*\b")           # B12, A4, 400
PHRASE = re.compile(r"\b([A-Za-z][A-Za-z-]+)\s+(\d+)\b")      # Terminal 2, row 4
LETTER_PHRASE = re.compile(r"\b([A-Za-z][A-Za-z-]+)\s+([A-Z])\b")  # zone B, exit C
SPLIT  = re.compile(r"\b(?:is|are)\b", re.IGNORECASE)


def _clean_words(text):
    return re.findall(r"[A-Za-z][A-Za-z-]*|\d+", text)


def keywords_for_answer(text):
    if not text:
        return []
    kws, seen = [], set()

    def add(kw):
        low = kw.lower()
        if low not in seen and low not in GENERIC:
            seen.add(low)
            kws.append(kw)

    used_numbers = set()
    for word, num in PHRASE.findall(text):
        if word.lower() in SPATIAL | UNITS | GENERIC:
            continue
        add(f"{word} {num}")
        used_numbers.add(num)
    used_letters = set()
    for word, letter in LETTER_PHRASE.findall(text):
        if word.lower() in SPATIAL | UNITS | GENERIC:
            continue
        add(f"{word} {letter}")
        used_letters.add(letter)

    has_code = False
    for tok in CODE.findall(text):
        if tok.isdigit():
            if tok not in used_numbers:
                add(tok)
        else:
            has_code = True
            add(tok)

    parts = SPLIT.split(text, maxsplit=1)
    if len(parts) == 2:
        subject, predicate = parts
        subj_words = [w for w in _clean_words(subject)
                      if w.lower() not in GENERIC and not w.isdigit()]
        if subj_words and subj_words[-1].lower() not in PRONOUNS:
            if not (has_code or used_numbers or used_letters):
                add(" ".join(subj_words))
        for w in subj_words:
            if (w[0].isupper() and subject.strip().split()[0] != w
                    and not CODE.search(w) and len(w) > 1):
                add(w)
        pred_words = [w for w in _clean_words(predicate)
                      if w.lower() not in GENERIC and not w.isdigit()]
        if (pred_words and len(pred_words[-1]) > 1
                and not (has_code or used_numbers or used_letters)):
            add(pred_words[-1])

    words = text.split()
    for i, w in enumerate(words):
        wc = re.sub(r"[^A-Za-z0-9-]", "", w)
        if (i > 0 and wc[:1].isupper() and wc.lower() not in GENERIC
                and not CODE.search(wc) and len(wc) > 1):
            add(wc)
    return kws


def keywords_for_case(case):
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


# ---------------------------------------------------------------------------
# Case construction helpers
# ---------------------------------------------------------------------------
CASES = []

def case(query, mode, edge, fog, edge_failed=False, fog_failed=False,
         must_include=None):
    c = {
        "id": len(CASES) + 1,
        "query": query,
        "mode": mode,
        "edge_answer": edge,
        "fog_answer": fog,
        "edge_failed": edge_failed,
        "fog_failed": fog_failed,
    }
    c["must_include"] = (must_include if must_include is not None
                         else keywords_for_case(c))
    CASES.append(c)


# ---------------------------------------------------------------------------
# 1) Your original 8 cases, verbatim (ids 1-8)
# ---------------------------------------------------------------------------
for old in json.load(open("original_testset.json", encoding="utf-8")):
    CASES.append(old)

# ---------------------------------------------------------------------------
# 2) Sequential: fog gives directions to the personal fact  (16 cases)
# ---------------------------------------------------------------------------
seq = [
 ("Where is my gate?",
  "Your gate is D7",
  "it's in Terminal 3, up the escalator, 250 meters ahead"),
 ("Where is my gate?",
  "Your gate is E15",
  "it's past the duty-free shops, 300 meters straight ahead"),
 ("Where does my flight board?",
  "Your flight boards at gate F2",
  "it's to the right after passport control, 120 meters ahead"),
 ("Where is my connecting flight?",
  "Your connection departs from gate A9",
  "it's one level down, 500 meters through the corridor"),
 ("Where do I pick up my bag?",
  "Your bag arrives at carousel 5",
  "it's in the arrivals hall, 60 meters past customs"),
 ("Where is my baggage claim?",
  "Your baggage claim is carousel 2",
  "it's downstairs to the left, 90 meters ahead"),
 ("Where does my shuttle leave from?",
  "Your shuttle is the Hilton shuttle",
  "it departs from door 6, 80 meters to the right"),
 ("Where is my train?",
  "Your train is the RE7 to the city center",
  "it leaves from platform 2, one level below arrivals"),
 ("Where is my lounge?",
  "Your lounge is the Delta Sky Club",
  "it's on level 3, 150 meters past security"),
 ("Where do I drop my bag?",
  "Your bag drop is at counter 12",
  "it's in the departures hall, 40 meters to the left"),
 ("Where is my check-in?",
  "Your airline is United",
  "the United check-in desks are at row 8, straight ahead"),
 ("Where is my bus stop?",
  "Your bus is the 747 airport express",
  "it stops at bay 3, outside exit C, 70 meters ahead"),
 ("Where do I collect my rental car?",
  "Your rental company is Hertz",
  "the Hertz counter is in the parking garage, 200 meters via the skybridge"),
 ("Where is my hotel pickup?",
  "Your pickup is the Marriott van",
  "it waits at door 4 of arrivals, 50 meters to the right"),
 ("Where is my boarding area?",
  "Your boarding area is zone B",
  "it's behind the food court, 110 meters ahead on the left"),
 ("Where is passport control for my flight?",
  "Your flight uses the international wing",
  "passport control is up the ramp, 90 meters ahead"),
]
for q, e, f in seq:
    case(q, "sequential", e, f)

# ---------------------------------------------------------------------------
# 3) Sequential NODE-MERGE: fog restates the edge's code  (6 cases)
#    These stress the graph approach's de-duplication rule.
# ---------------------------------------------------------------------------
merge = [
 ("Where is my gate?",
  "Your gate is B3",
  "Gate B3 is in Terminal 2, 180 meters ahead on the right"),
 ("Where is my gate?",
  "Your gate is C11",
  "Gate C11 is past the bookstore, 220 meters straight ahead"),
 ("Where is my carousel?",
  "Your carousel is carousel 7",
  "Carousel 7 is at the far end of arrivals, 130 meters ahead"),
 ("Where is my platform?",
  "Your platform is platform 4",
  "Platform 4 is downstairs, 100 meters to the left"),
 ("Where does my flight leave from?",
  "Your flight leaves from gate D20",
  "Gate D20 is in Terminal 1, 350 meters via the moving walkway"),
 ("Where is my counter?",
  "Your counter is counter 9",
  "Counter 9 is in the departures hall, 45 meters to the right"),
]
for q, e, f in merge:
    case(q, "sequential", e, f)

# ---------------------------------------------------------------------------
# 4) Parallel: personal item + independent nearby thing  (14 cases)
# ---------------------------------------------------------------------------
par = [
 ("Is my suitcase near a bench?",
  "Your suitcase is a red hardshell",
  "a bench is 15 meters to your right"),
 ("Is there water near my gate seat?",
  "Your seat is by the window at the gate",
  "a water fountain is 25 meters to your left"),
 ("Where is my medication and a pharmacy?",
  "Your medication is in the front pocket of your backpack",
  "a pharmacy is 60 meters ahead on the left"),
 ("Where is my boarding pass and the gate desk?",
  "Your boarding pass is in your phone wallet",
  "the gate desk is 15 meters straight ahead"),
 ("Where is my wallet and an ATM?",
  "Your wallet is in your jacket pocket",
  "an ATM is 35 meters to your right"),
 ("Is there coffee near my gate?",
  "Your gate is B6",
  "a coffee shop is 30 meters to your left"),
 ("Where can my guide dog go?",
  "Your dog is a yellow labrador",
  "the pet relief area is 85 meters ahead near exit B"),
 ("Where is my umbrella and the taxi stand?",
  "Your umbrella is in the side pocket of your bag",
  "the taxi stand is 55 meters outside the main doors"),
 ("Is there a quiet room near my gate?",
  "Your gate is A2",
  "a quiet room is 70 meters ahead on the right"),
 ("Where are my headphones and a charging spot?",
  "Your headphones are in the top pouch",
  "a charging station is 20 meters behind you"),
 ("Where is my passport and the help desk?",
  "Your passport is in your inner coat pocket",
  "the information desk is 45 meters to your left"),
 ("Is there food near my gate?",
  "Your gate is F9",
  "a pizza restaurant is 40 meters to your right"),
 ("Where is my stroller and the elevator?",
  "Your stroller is at the gate check rack",
  "the elevator is 30 meters ahead"),
 ("Where is my jacket and a restroom?",
  "Your jacket is on seat 21A",
  "a restroom is 65 meters ahead on the left"),
]
for q, e, f in par:
    case(q, "parallel", e, f)

# ---------------------------------------------------------------------------
# 5) CONTRADICTIONS: edge and fog disagree  (6 cases, week-7 hard cases)
#    A good fused answer must surface BOTH values (never silently pick one),
#    so must_include requires both conflicting anchors.
# ---------------------------------------------------------------------------
contra = [
 ("Where is my gate?",
  "Your gate is B12",
  "the departure board shows your flight at gate B14"),
 ("Where is my gate?",
  "Your gate is C4",
  "the gate agent announced boarding at gate C6"),
 ("Where do I pick up my bag?",
  "Your bag arrives at carousel 3",
  "the arrivals screen lists your flight at carousel 5"),
 ("When does my flight board?",
  "Your flight boards at 14:20",
  "the departure board shows boarding at 14:45"),
 ("Where is my seat?",
  "Your seat is 12A",
  "the boarding pass scanner shows seat 14C"),
 ("Where is my platform?",
  "Your platform is platform 2",
  "the station display shows platform 5 for your train"),
]
for q, e, f in contra:
    case(q, "sequential", e, f)

# ---------------------------------------------------------------------------
# 6) Failures  (10 cases)
# ---------------------------------------------------------------------------
fail_fog = [
 ("Where is my gate?", "Your gate is A7"),
 ("Where is my carousel?", "Your carousel is carousel 4"),
 ("Which airline am I flying?", "Your airline is Lufthansa"),
 ("Where is my seat?", "Your seat is 22F"),
]
for q, e in fail_fog:
    case(q, "sequential", e, None, fog_failed=True)

fail_edge = [
 ("Where is the nearest restroom?", "the restroom is 40 meters ahead on the left"),
 ("Where is the taxi stand?", "the taxi stand is 60 meters outside exit A"),
 ("Where can I charge my phone?", "a charging station is 25 meters to your right"),
 ("Where is the escalator?", "the escalator is 35 meters straight ahead"),
]
for q, f in fail_edge:
    case(q, "parallel", None, f, edge_failed=True)

case("Where is my gate?", "sequential", None, None,
     edge_failed=True, fog_failed=True)
case("Where is my bag?", "parallel", None, None,
     edge_failed=True, fog_failed=True)

# ---------------------------------------------------------------------------
# Write the file
# ---------------------------------------------------------------------------
with open("fusion_testset.json", "w", encoding="utf-8") as fh:
    json.dump(CASES, fh, indent=2, ensure_ascii=False)

n_seq = sum(1 for c in CASES if c["mode"] == "sequential" and not (c["edge_failed"] or c["fog_failed"]))
n_par = sum(1 for c in CASES if c["mode"] == "parallel" and not (c["edge_failed"] or c["fog_failed"]))
n_fail = sum(1 for c in CASES if c["edge_failed"] or c["fog_failed"])
print(f"wrote fusion_testset.json with {len(CASES)} cases")
print(f"  sequential (both ok): {n_seq}   parallel (both ok): {n_par}   failure cases: {n_fail}")
print(f"  includes 6 node-merge cases and 6 contradiction cases")