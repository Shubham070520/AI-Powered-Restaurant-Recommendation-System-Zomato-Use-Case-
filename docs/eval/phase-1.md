# Phase 1 Evaluation — Data Layer

**Goal:** Load Hugging Face dataset, preprocess to `Restaurant`, serve from store.  
**Plan reference:** [implementation-plan.md](../implementation-plan.md) § Phase 1  
**Edge cases:** [edgecase.md](../edgecase.md) §1 (D-01–D-18)

---

## Prerequisites

- Phase 0 PASS
- Network access for first HF download (or valid cache file)

---

## Automated evaluation

| # | Check | Command / action | Pass |
|---|--------|------------------|------|
| A1-1 | Preprocessor tests | `pytest tests/test_preprocessor.py -q` | All pass |
| A1-2 | Smoke load | `python -m src.data.loader` (or project smoke script) | Prints N > 0 |
| A1-3 | Model validation | Unit test: invalid row skipped without crash | Pass |
| A1-4 | Cuisine split | Test `"A, B, C"` → 3 tokens | Pass |
| A1-5 | Budget tier | Row with cost 400 → `low`; 1200 → `medium` | Per threshold table |

---

## Manual evaluation

| # | Criterion | Steps | Pass |
|---|-----------|-------|------|
| M1-1 | Real dataset load | Run smoke script on HF dataset | N > 0 restaurants |
| M1-2 | Field completeness | Sample 10 records: all have `id`, `name`, `location` | 100% |
| M1-3 | City distribution | Print count for 2 known cities (e.g. Bangalore, Delhi) | Non-zero if in data |
| M1-4 | Cache round-trip | Run load twice with `DATA_CACHE_PATH` set | Second run faster |
| M1-5 | Download failure | (Optional) Offline without cache | Clear error D-01 |

---

## Blocker criteria

- [ ] **B1-1** Store contains > 0 restaurants after successful load.
- [ ] **B1-2** Every stored record has non-empty `id`, `name`, `location`.
- [ ] **B1-3** Preprocessor does not crash on messy rows (D-07, D-11, D-12).
- [ ] **B1-4** `budget_tier` set when `cost_for_two` is valid.
- [ ] **B1-5** Loader failure produces actionable error (D-01, D-02).

---

## Important criteria

- [ ] **I1-1** Location matching key is case-insensitive (D-13).
- [ ] **I1-2** Skipped rows logged or counted (D-04, D-05).
- [ ] **I1-3** Dataset column mapping documented in code or `dataset-notes.md` (D-03).

---

## Test data scenarios

| Scenario | Input | Expected |
|----------|--------|----------|
| Valid row | Complete raw row | `Restaurant` with all core fields |
| Null rating | Missing rating | Policy: skip or null per design |
| Null cost | Missing cost | `budget_tier` null |
| Multi-cuisine | `"North Indian, Chinese"` | `len(cuisines) >= 2` |

---

## Artifacts to demo

- Smoke output: `Loaded N restaurants; <city>: M`
- Optional: `tests/test_preprocessor.py`

---

## Phase gate

**PASS** → Phase 2 when blockers met and M1-1, M1-2 succeed.
