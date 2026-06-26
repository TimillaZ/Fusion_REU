# graph_fuse.py
#
# APPROACH 3: "graph fusion" -- a small, deterministic, fully-local merge
# inspired by the syntax-based sentence-fusion line of work (Filippova & Strube
# 2008; Cheung & Penn 2014, "Unsupervised Sentence Enhancement").
#
# Those papers build a dependency GRAPH from several sentences, MERGE nodes that
# share a lemma (so a fact stated twice appears once), then linearise the graph
# back into one sentence. The heavy machinery they use -- CoreNLP, an ILP solved
# with CPLEX, distributional models trained on Gigaword -- is overkill for our
# job: we fuse exactly TWO short answers that the router has already aligned, and
# it must run on an edge device. So we keep ONLY the part that actually helps us:
#
#   * node merge  -> if the surroundings (fog) answer already restates the
#                    personal (edge) fact, say that fact ONCE  (their Step 2).
#   * linearise   -> put the most actionable (spatial) clause first, resolve a
#                    dangling pronoun, and join cleanly  (their Step 5, in spirit).
#
# This is the answer to open question #5 in the Week-3 report (sequential
# de-duplication) and a deterministic third column for the comparison table:
# it can't hallucinate and never varies run-to-run, unlike the LLM.
#
# DEPENDENCY (optional): spaCy + the small English model give better anchor
# detection (named entities, proper nouns).  Install once with:
#     pip install spacy
#     python -m spacy download en_core_web_sm
# If spaCy is NOT installed, this file STILL works: it falls back to a regex
# anchor finder (slightly less robust), exactly the way llm_fuse falls back to
# the template when Ollama isn't running. Nothing here ever crashes the pipeline.

import re

from fusion_engine import TierResult, fuse, tidy   # reuse the box + failure paths


# ---------------------------------------------------------------------------
# Try to load spaCy once. If it isn't there, nlp stays None and we use regex.
# ---------------------------------------------------------------------------
try:
    import spacy
    try:
        _NLP = spacy.load("en_core_web_sm")
    except Exception:
        _NLP = None          # spaCy installed but model not downloaded
except Exception:
    _NLP = None              # spaCy not installed at all


# A leading vague pronoun the fog answer often opens with ("it's in Terminal 2").
_PRONOUN_OPENER = re.compile(
    r"^\s*(it's|it is|it\u2019s|that's|that is|they're|they are)\b",
    re.IGNORECASE,
)

# Words that signal an actionable, spatial instruction (the thing to walk to).
_SPATIAL = re.compile(
    r"\b(meters?|metres?|left|right|ahead|straight|behind|forward|steps?|"
    r"north|south|east|west|past|opposite|next to|near)\b",
    re.IGNORECASE,
)

# An "anchor" is a specific, identifying token: an alphanumeric code (B12, A4),
# a bare number (3, 20), or a Capitalised word that isn't sentence-initial
# (Delta, Terminal). These are the nodes worth merging on.
_ALNUM = re.compile(r"^[A-Za-z]*\d[A-Za-z\d]*$")     # has a digit, e.g. B12, A4, C9
_NUMBER = re.compile(r"^\d+$")


# ---------------------------------------------------------------------------
# Pull the anchors out of a sentence. Returns a list of (surface, lower) pairs
# so we can both match case-insensitively AND substitute with original casing.
# ---------------------------------------------------------------------------
def extract_anchors(text):
    if _NLP is not None:
        return _anchors_spacy(text)
    return _anchors_regex(text)


def _anchors_spacy(text):
    doc = _NLP(text)
    anchors = []
    seen = set()

    def add(tok_text):
        low = tok_text.lower()
        if low and low not in seen:
            seen.add(low)
            anchors.append((tok_text, low))

    # named entities first (Delta, Terminal 2, ...)
    for ent in doc.ents:
        add(ent.text)
    # then proper nouns, numbers, and alphanumeric codes
    for tok in doc:
        if tok.is_stop or tok.is_punct:
            continue
        if tok.pos_ in ("PROPN", "NUM") or _ALNUM.match(tok.text):
            add(tok.text)
    return anchors


def _anchors_regex(text):
    anchors = []
    seen = set()
    words = re.findall(r"[A-Za-z0-9]+", text)
    for i, w in enumerate(words):
        is_alnum = bool(_ALNUM.match(w))
        is_number = bool(_NUMBER.match(w))
        # capitalised but not the very first word of the sentence
        is_propn = (i > 0 and w[0].isupper())
        if is_alnum or is_number or is_propn:
            low = w.lower()
            if low not in seen:
                seen.add(low)
                anchors.append((w, low))
    return anchors


def _primary_anchor(anchors):
    # Prefer an alphanumeric code (B12) -> then anything else. This is the token
    # we use to replace a dangling pronoun.
    for surface, low in anchors:
        if _ALNUM.match(surface):
            return surface
    return anchors[0][0] if anchors else None


# ---------------------------------------------------------------------------
# SEQUENTIAL merge: the fog answer elaborates on the edge fact.
# ---------------------------------------------------------------------------
def _fuse_sequential(edge_text, fog_text):
    anchors = extract_anchors(edge_text)
    fog_low = fog_text.lower()

    # NODE MERGE (F&S / Cheung & Penn Step 2): if the fog answer already names
    # every personal anchor, the edge sentence is redundant -- state it ONCE.
    if anchors and all(low in fog_low for (_, low) in anchors):
        return tidy(fog_text) + "."

    # Otherwise we must keep both facts. If fog opens with a dangling pronoun
    # ("it's in Terminal 2"), resolve it to the edge's anchor so the two facts
    # read as one thought AND the personal anchor survives the merge.
    match = _PRONOUN_OPENER.match(fog_text)
    primary = _primary_anchor(anchors)
    if match and primary is not None:
        verb = "are" if match.group(1).lower() in ("they're", "they are") else "is"
        rewritten = f"{primary} {verb} " + fog_text[match.end():].lstrip()
        return tidy(rewritten) + "."

    # No clean merge available -> connect as a flowing thought (like the template).
    return f"{tidy(edge_text)} \u2014 {tidy(fog_text)}."


# ---------------------------------------------------------------------------
# PARALLEL merge: two independent facts -> list them, actionable one first.
# ---------------------------------------------------------------------------
def _lower_initial(text):
    # Lowercase the first letter unless the clause starts with a code/entity we
    # want to keep capitalised (B12, Delta). Cheap heuristic: leave it capital
    # if the first word is an anchor of itself, else lowercase it for mid-sentence.
    first_word = re.match(r"\s*([A-Za-z0-9]+)", text)
    if first_word:
        w = first_word.group(1)
        if _ALNUM.match(w) or (len(w) > 1 and w.isupper()):
            return text  # keep "B12 ...", "USB ..." capitalised
    stripped = text.lstrip()
    return stripped[:1].lower() + stripped[1:] if stripped else text


def _fuse_parallel(edge_text, fog_text):
    edge_spatial = bool(_SPATIAL.search(edge_text))
    fog_spatial = bool(_SPATIAL.search(fog_text))

    # GUIDELINE: most actionable (spatial) information first. If only the fog
    # answer carries directions, lead with it; otherwise keep edge first (stable).
    if fog_spatial and not edge_spatial:
        first, second = fog_text, edge_text
    else:
        first, second = edge_text, fog_text

    return f"{tidy(first)}, and {_lower_initial(tidy(second))}."


# ---------------------------------------------------------------------------
# The public function -- same shape as fuse() and llm_fuse(), so it's a drop-in.
# ---------------------------------------------------------------------------
def graph_fuse(edge: TierResult, fog: TierResult, mode: str) -> str:
    # MAMMQA ABSTENTION: if a tier failed or is empty, do not try to merge --
    # reuse the safe template handling for every failure case.
    if not (edge.is_usable() and fog.is_usable()):
        return fuse(edge, fog, mode)

    if mode == "sequential":
        return _fuse_sequential(edge.text, fog.text)
    return _fuse_parallel(edge.text, fog.text)