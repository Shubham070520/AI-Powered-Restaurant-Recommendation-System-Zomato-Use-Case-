# Phase 3 Evaluation — LLM Integration Layer

**Goal:** Prompts, LLM client, JSON parser with id validation.  
**Plan reference:** [implementation-plan.md](../implementation-plan.md) § Phase 3  
**Edge cases:** [edgecase.md](../edgecase.md) §4 (L-*)

---

## Prerequisites

- Phase 2 PASS
- `LLM_API_KEY` for live tests (optional if mock-only gate)

---

## Automated evaluation

| # | Check | Command | Pass |
|---|--------|---------|------|
| A3-1 | Parser tests | `pytest tests/test_parser.py -q` | All pass |
| A3-2 | Valid JSON fixture | Parse `llm_valid_response.json` | Structured result |
| A3-3 | Fenced JSON | Parse `llm_fenced_json.txt` | L-07 pass |
| A3-4 | Invalid ids | Parser drops unknown `restaurant_id` | L-10 |
| A3-5 | Prose-only response | Parse fails gracefully | L-06 |
| A3-6 | Prompt content test | Assert system/user contains “only provided restaurants” | L-15 |

---

## Manual evaluation (live LLM)

| # | Criterion | Steps | Pass |
|---|-----------|-------|------|
| M3-1 | Toy integration script | 3–5 hard-coded candidates + fixed preferences | Parseable JSON |
| M3-2 | Summary present | Response includes `summary` string | Non-empty most runs |
| M3-3 | Explanations reference prefs | Read explanations for cuisine/budget/rating | Plausible |
| M3-4 | No unknown ids | All `restaurant_id` in candidate set | 100% |
| M3-5 | Missing API key | Run without key | Clear error L-01 |

---

## Manual evaluation (mock LLM — acceptable for CI gate)

| # | Criterion | Steps | Pass |
|---|-----------|-------|------|
| M3-6 | Mock client | Return fixed JSON string | Parser + schema OK |

---

## Blocker criteria

- [ ] **B3-1** Parser accepts valid model output schema (`summary`, `recommendations[]`).
- [ ] **B3-2** Unknown `restaurant_id` rejected or dropped with warning (L-10).
- [ ] **B3-3** Prompt forbids inventing restaurants (L-15).
- [ ] **B3-4** Markdown-fenced JSON handled (L-07).
- [ ] **B3-5** LLM client supports timeout and at least one retry on transient failure (L-03).

---

## Important criteria

- [ ] **I3-1** Parse retry on malformed JSON once (L-06, L-08).
- [ ] **I3-2** Duplicate ranks/ids handled (L-11, L-12).
- [ ] **I3-3** 401/429 surfaced without leaking API key (L-02, L-04, E-05).

---

## Parser fixture checklist

| Fixture | Expected outcome |
|---------|------------------|
| Valid bare JSON | Success |
| ```json ... ``` wrapped | Success |
| Extra unknown id | Id dropped |
| All ids invalid | Error / empty valid set |
| Missing `recommendations` key | Validation error |

---

## Artifacts to demo

- Integration script output: ranks + explanations for 3–5 candidates
- `tests/test_parser.py` green

---

## Phase gate

**PASS** → Phase 4 when blockers + A3-1 pass, and M3-1 **or** M3-6 passes.
