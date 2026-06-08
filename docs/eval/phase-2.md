# Phase 2 Evaluation — Domain Layer (Preferences & Filtering)

**Goal:** Validate preferences, hard-filter restaurants, build candidate DTOs.  
**Plan reference:** [implementation-plan.md](../implementation-plan.md) § Phase 2  
**Edge cases:** [edgecase.md](../edgecase.md) §2–3 (P-*, F-*)

---

## Prerequisites

- Phase 1 PASS (`RestaurantStore` loaded in tests)

---

## Automated evaluation

| # | Check | Command | Pass |
|---|--------|---------|------|
| A2-1 | Filter tests | `pytest tests/test_filters.py -q` | All pass |
| A2-2 | Validation tests | Invalid budget/location raise `ValidationError` | Pass |
| A2-3 | Empty filter | Preferences with impossible combo → `candidates == []` | Pass |
| A2-4 | Truncation | > MAX matches → output length == MAX | Pass |
| A2-5 | Truncation order | Lower-rated venues dropped before higher | Pass |
| A2-6 | Candidate shape | Keys only: id, name, cuisines, rating, cost, budget_tier, location | Pass |

---

## Manual evaluation

| # | Criterion | Steps | Pass |
|---|-----------|-------|------|
| M2-1 | Filter script demo | Load store → apply Bangalore/medium/Italian/4.0 | Prints count + 3 candidates |
| M2-2 | No cuisine filter | Omit cuisine → more candidates than with Italian | True |
| M2-3 | Unknown city | `location=ZZZ_NoCity` | Zero candidates + message |
| M2-4 | Case insensitivity | `location=bangalore` vs `Bangalore` | Same count (P-13 casing for match) |
| M2-5 | Boundary rating | `min_rating=4.0` includes 4.0-rated rows | F-09 |

---

## Blocker criteria

- [ ] **B2-1** Empty `location` rejected (P-01, P-02).
- [ ] **B2-2** Invalid `budget` rejected (P-03).
- [ ] **B2-3** No returned restaurant violates location, budget, cuisine, or min_rating filters.
- [ ] **B2-4** Zero matches return message; documented that LLM will not run (F-01).
- [ ] **B2-5** Truncation respects `MAX_CANDIDATES_FOR_LLM` (F-03).

---

## Important criteria

- [ ] **I2-1** `top_k` default 5, capped at 10 (P-08, P-09).
- [ ] **I2-2** Stable sort on rating ties (F-04).
- [ ] **I2-3** Candidates JSON-serializable for prompts (F-11).

---

## Filter matrix (minimum manual matrix)

| Location | Budget | Cuisine | Min rating | Expected |
|----------|--------|---------|------------|----------|
| Valid city | medium | Italian | 4.0 | Subset only Italian-ish, rating ≥ 4 |
| Valid city | low | — | — | Only low tier |
| Invalid | medium | — | — | Empty |
| Valid city | high | RareCuisineXYZ | — | Empty or very small |

---

## Artifacts to demo

- Script output: candidate count + sample JSON (no LLM)

---

## Phase gate

**PASS** → Phase 3 when blockers + A2-1 pass.
