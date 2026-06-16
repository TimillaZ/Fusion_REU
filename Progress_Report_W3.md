# Response Fusion Engine — Progress Report

**Author:** Illango Zaruba — Fusion Component Lead
**Project:** Semantic Query Routing for Resource-Aware Edge–Fog–Cloud Systems (NSF IRES, HPCC Lab / IMDEA)
**Status as of:** Week 3 (start of the development phase)

---

## 1. What this component is

The overall project routes a user's question across three tiers — **Edge** (personal, private data), **Fog** (environmental/spatial data), and **Cloud** (heavy fallback) — for an assistive scenario: a blind traveler using smart glasses in an airport.

This report covers **only the Response Fusion Engine** (Step 3 / "hybrid response handling"). The router and the labeled query dataset are owned by teammates. The fusion engine's job begins *after* a mixed query has been split and each tier has answered: it takes the **personal (edge) answer** and the **environmental (fog) answer** and merges them into **one natural spoken sentence**, while handling failures and protecting privacy.

### Two design conditions
- **The Raspberry Pi now hosts the Fog tier** (it previously hosted Edge). Personal data and the fusion engine therefore live on the **laptop** (now the Edge tier). The privacy rules are unchanged in spirit — "personal text never leaves Edge," "fusion runs on Edge" — they simply map to different hardware now.
- **No Raspberry Pi is available yet.** Everything runs on one laptop: Edge and Fog as separate local processes, with network latency *injected in software*. The design is config-driven (the Fog address is a variable), so when a Pi arrives, the Fog service moves to it by changing one setting — no code rewrite.

---

## 2. What has been built

A working, runnable, measurable system in plain Python — **no model training, no math, and no Pi required.** The only external tool is a small local language model (Ollama) used by one of the fusion approaches.

| File | Purpose |
|---|---|
| `fusion_engine.py` | Core: the `TierResult` data structure (one tier's answer) and `fuse()` — **Approach 1 (template)** plus all graceful-failure handling. |
| `try_it.py` | Runs `fuse()` on hand-set examples (normal cases + failure cases). |
| `tiers.py` | Pretend Edge/Fog tiers that take time, plus `run_tier()` — a **timeout wrapper** so failure happens on its own when a tier is too slow. |
| `try_timeout.py` | Demonstrates real timeout-driven failure (no manual `failed=True`). |
| `try_parallel.py` | Runs Edge and Fog **concurrently** and times it against running them one-after-another, showing the latency benefit. |
| `fusion_testset.json` | The **dataset** for this component: 8 cases (parallel, sequential, fog-fail, edge-fail, both-fail), each with the key facts that should survive the merge. |
| `run_testset.py` | Scores **merge correctness** — for how many cases did all required facts survive? |
| `llm_fuse.py` | **Approach 2 (LLM synthesis)**: asks a local model to write one sentence from the two answers. |
| `try_llm.py` | Shows the template result and the LLM result side by side. |
| `compare_approaches.py` | Runs the dataset through every approach and prints a **summary comparison table**. |

### Capabilities delivered
- Two execution modes: **parallel** and **sequential**.
- **Graceful failure** for every case: fog-only, edge-only, both-failed, all with calm spoken fallbacks instead of crashes.
- **Timeout-driven** failure (a tier that misses its deadline is marked failed automatically).
- **Concurrent** tier execution with a shared deadline (parallel mode is faster than sequential by design).
- A **dataset** owned by this component, plus an automated **score**.
- A **comparison harness** that scores any number of approaches against the dataset.

---

## 3. How the design follows the papers

The fusion engine is built directly from the assigned papers; these are not background reading but concrete design constraints.

| Source | Principle taken | Where it lives in the code |
|---|---|---|
| **MAMMQA** | The aggregator is **question-agnostic** (sees only the evidence, never the original question) and **abstains** when a tier has no answer rather than inventing one. | `TierResult` carries no question field; `llm_fuse()` skips the model entirely when a tier failed and uses the safe fallback. |
| **GSA** | Merge by **generating one new sentence** from the candidates — no judging, no "pick the best." | `llm_fuse()` / `build_prompt()` (Approach 2). |
| **Fusion guideline** | One screen-reader sentence; most important fact first; spatial language, not visual; use only what's given. | The prompt rules in `build_prompt()`. |
| **Privacy rule (post-swap)** | Personal text must never leave the Edge device; fusion runs on Edge. | A **local** model is used (Ollama on the laptop), so personal text never goes to the Pi; fusion code is co-located with the edge side. |
| **LLM-Blender / MoA** | Considered and **deliberately not used** for the core merge — their fusers are heavy/trained and unsuitable for an edge device. MoA's "synthesize, don't replicate" phrasing informs the prompt. | Documented design choice; informs Approach 5 later. |

---

## 4. Current results

Metric implemented so far: **merge correctness** (did every required fact survive the merge?), scored automatically over the 8-case dataset.

| Approach | Merge correctness |
|---|---|
| Template (Approach 1) | 100% (8/8) |
| LLM synthesis (Approach 2) | to be measured on the development laptop |

### Important caveat — and a real finding
The template scores 100% because it copies text **verbatim**, so every exact keyword survives. The LLM **rephrases** ("400 meters" → "four hundred meters", reordering, etc.). Because the merge-correctness check looks for exact strings, the LLM can produce a perfectly correct, more natural answer and still score lower **on this metric**.

This is not the LLM being worse — it is the **metric being blunt**. It measures *fact retention*, not *quality*. This is precisely why the evaluation plan lists **naturalness** as a separate metric: no single number captures both "the facts are there" and "it sounds good read aloud." This tension is a genuine result worth reporting, and it motivates the remaining metrics.

---

## 5. How to run it

1. (One time) Install **Ollama** from ollama.com, then `ollama pull gemma2:2b`.
2. Put all the files above in one folder.
3. Quick checks:
   - `python try_it.py` — basic fusion + failure handling.
   - `python try_timeout.py` — timeout-driven failure.
   - `python try_parallel.py` — concurrent execution + timing.
   - `python run_testset.py` — merge-correctness score (template).
   - `python try_llm.py` — template vs LLM, side by side (needs Ollama running).
   - `python compare_approaches.py` — the comparison table.

**Note on Python version:** the code uses `Optional[str]` (via `from typing import Optional`) rather than `str | None`, so it runs on Python 3.8+ as well as newer versions.

---

## 6. Position on the overall plan

The full component plan has 13 steps. Progress so far:

- **Step 2 — input contract:** done (`TierResult`, mode, deliberately no question field).
- **Step 4 — fusion approaches:** 2 of 5 done (template, LLM synthesis).
- **Step 5 — failure handling:** done (all failure cases + timeout-driven).
- **Step 7 — latency handling:** seeded (concurrent execution; full draft-then-inject still to do).
- **Step 8 — dataset/fixtures:** done (owned by this component).
- **Step 9 — evaluation:** 1 of 4 metrics done (merge correctness), with a working comparison harness.

A running, measurable system exists. The remaining work is additive on top of a foundation that already works.

---

## 7. What's next

In priority order:
1. **Naturalness metric** — reuse the local model as a *judge* (rubric: one sentence? spatial not visual? important info first? natural aloud?). This is the metric where the LLM approach should pull ahead of the template.
2. **Latency metric** — formalize the timing already written in `try_parallel.py` into a recorded number against the budget.
3. **Graceful-failure metric** — score the failure cases for correct degraded behavior.
4. **Approaches 3 and 4** (confidence-ordering, slot-filling) — both plain Python — to reach four approaches.
5. **Harder dataset cases** — contradictions and sequential near-duplicates, where a plain template should start to fail and a smart merge should win.
6. **Full comparison table** — 5 approaches × 4 metrics (the core deliverable).
7. **Integration** with the real router output and real tiers (Phase 3) — a swap, not a rewrite, thanks to the fixed contract.
8. **Approach 5** (multi-agent deliberation) — optional, heaviest; quality ceiling.
9. **Pi deployment** — one config change when the board is available.
10. **Paper / report draft** (Phase 4).

---

## 8. Open questions for the advisor / team

- **Privacy rules** (marked "(?)" in the guideline): confirm which are enforced, especially deleting vs. keeping response history.
- **Confidence scores:** do Edge and Fog return calibrated confidences? Approach 3 and the low-confidence fallback depend on it.
- **Structured vs. free text:** Approach 4 (slot-filling) needs structured fields, but tiers currently return free text — decide whether Fog can return structured slots.
- **Router → fusion contract:** lock the `TierResult` + mode schema with the framework teammate before Phase 3 integration.
- **Sequential de-duplication:** confirm expected phrasing when the fog answer already restates the personal detail.