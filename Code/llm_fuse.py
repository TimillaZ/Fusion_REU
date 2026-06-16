# llm_fuse.py
#
# This is the "smart" merge: instead of gluing two sentences with a template,
# we ask a small LANGUAGE MODEL (running locally on your laptop) to write ONE
# natural sentence that combines them.
#
# This is NOT training and NOT math. We send text to the model and get text
# back, like calling a small program on your own machine.
#
# Where the papers show up is marked in CAPS in the comments below.
#
# Uses only Python's standard library (urllib, json) -- nothing to pip install.
# It does need the Ollama app installed and a model pulled (see the chat steps).

import os
import json
import urllib.request

from fusion_engine import TierResult, fuse

# Which local model to use. You can change this without touching code by setting
# an environment variable, but the default is fine.
MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")


# ---------------------------------------------------------------------------
# Build the instruction we send to the model.
# ---------------------------------------------------------------------------
def build_prompt(edge_text: str, fog_text: str, mode: str) -> str:
    # MAMMQA: notice the ORIGINAL QUESTION is NOT included. The aggregator
    # grounds only on the evidence (the two answers). This is on purpose.
    #
    # GUIDELINE: blind user, ONE spoken sentence, important info first,
    # spatial (not visual) language, use only what's given.
    prompt = (
        "You combine two pieces of information for a blind traveler in an "
        "airport into ONE short sentence that will be read aloud by a screen "
        "reader.\n\n"
        f"Personal information: {edge_text}\n"
        f"Surroundings information: {fog_text}\n\n"
        "Rules:\n"
        "- Use ONLY the two pieces of information above. Do not add any fact "
        "that is not stated.\n"     # MAMMQA / GUIDELINE: no hallucination
        "- Output exactly ONE sentence.\n"
        "- Put the most important, actionable information first.\n"
        "- Use spatial directions (left, right, meters ahead). Never use "
        "visual words like 'see' or 'look'.\n"
        "- Keep it natural and concise.\n"
    )
    # In sequential mode the surroundings answer may repeat the personal detail
    # (e.g. it restates the gate). Tell the model to say each fact only once.
    if mode == "sequential":
        prompt += ("- The surroundings information may repeat the personal "
                   "detail; mention each fact only once.\n")
    prompt += "\nSentence:"
    return prompt


# ---------------------------------------------------------------------------
# Send the prompt to the local Ollama model and get its reply.
# ---------------------------------------------------------------------------
def call_ollama(prompt: str, model: str, timeout: int = 120) -> str:
    url = "http://localhost:11434/api/generate"   # Ollama's local address
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,                 # give us the whole answer at once
        "options": {"temperature": 0.2}  # low = steady, less random wording
    }).encode("utf-8")

    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    # The first call after starting Ollama can be slow (it loads the model),
    # which is why the timeout is generous.
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["response"].strip()


# ---------------------------------------------------------------------------
# Light tidy-up: models sometimes add quotes or stray line breaks.
# ---------------------------------------------------------------------------
def clean(text: str) -> str:
    text = text.strip().strip('"').strip()      # remove wrapping quotes/space
    text = " ".join(text.split())                # collapse newlines into spaces
    return text


# ---------------------------------------------------------------------------
# The main function: same shape as your template fuse(), so it's a drop-in swap.
# ---------------------------------------------------------------------------
def llm_fuse(edge: TierResult, fog: TierResult, mode: str) -> str:
    # MAMMQA ABSTENTION: if a tier failed or is empty, do NOT ask the model to
    # invent anything. Reuse your safe template handling for the failure cases.
    if not (edge.is_usable() and fog.is_usable()):
        return fuse(edge, fog, mode)

    # Both answers exist -> ask the model to synthesize one sentence (GSA).
    prompt = build_prompt(edge.text, fog.text, mode)
    try:
        return clean(call_ollama(prompt, MODEL))
    except Exception as error:
        # If the model isn't running yet, we don't crash -- we fall back to the
        # template so your pipeline always returns something.
        print("  [note] local model not reachable, used template instead:", error)
        return fuse(edge, fog, mode)