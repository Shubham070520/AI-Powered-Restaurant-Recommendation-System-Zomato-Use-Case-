# Phase 5 Evaluation — Presentation Layer (UI)

**Goal:** User can submit preferences and view AI recommendations in browser.  
**Plan reference:** [implementation-plan.md](../implementation-plan.md) § Phase 5  
**Edge cases:** [edgecase.md](../edgecase.md) §6 (U-*)

---

## Prerequisites

- Phase 4 PASS
- `LLM_API_KEY` configured for live demo

---

## Automated evaluation

| # | Check | Action | Pass |
|---|--------|--------|------|
| A5-1 | App starts | `streamlit run src/main.py` or `uvicorn` | No traceback |
| A5-2 | Store init once | Reload page; dataset not re-downloaded each click | Cached load |
| A5-3 | (Optional) E2E | Playwright/manual script documented | Optional |

---

## Manual evaluation — UI checklist

| # | Criterion | Steps | Pass |
|---|-----------|-------|------|
| M5-1 | Preference form | All fields: location, budget, cuisine, min rating, extras, top_k | Present |
| M5-2 | Submit flow | Fill valid prefs → Submit | Loading state shown |
| M5-3 | Results layout | Summary + per-restaurant cards | All visible |
| M5-4 | Required output fields | Name, cuisine, rating, estimated cost, explanation | Each card |
| M5-5 | Empty state | Unknown city / impossible filter | Friendly message U-05 |
| M5-6 | Validation | Submit empty location | Inline error U-03 |
| M5-7 | Missing API key | Remove key, submit | Actionable error U-06 |
| M5-8 | Security | Inspect browser network / page source | No API key exposed U-* |
| M5-9 | README run path | Follow README from clean clone | App runs in &lt; 15 min |

---

## Blocker criteria

- [ ] **B5-1** Non-technical user can complete one recommendation flow.
- [ ] **B5-2** All problem-statement display fields shown per restaurant.
- [ ] **B5-3** Empty filter shows empty state (not blank/hung).
- [ ] **B5-4** README documents install, `.env`, and run command.
- [ ] **B5-5** API keys server-side only (if FastAPI + frontend).

---

## Important criteria

- [ ] **I5-1** Loading indicator during LLM call (U-04).
- [ ] **I5-2** Double-submit mitigated (O-05).
- [ ] **I5-3** Location dropdown or autocomplete from store cities (optional).
- [ ] **I5-4** `candidates_considered` visible in UI or debug panel.

---

## Demo scenarios (record for submission)

| # | Preferences | Expected UX |
|---|-------------|---------------|
| 1 | Bangalore, medium, Italian, 4.0+ | 1–5 cards with explanations |
| 2 | Delhi, low, Chinese, none | Results or empty with message |
| 3 | Invalid city | Empty state, no crash |
| 4 | Empty location on submit | Validation error |

---

## Artifacts to demo

- Screenshot or short screen recording of scenario 1
- Updated `README.md`

---

## Phase gate

**PASS** → Phase 6 when all blockers and M5-1–M5-5 pass.
