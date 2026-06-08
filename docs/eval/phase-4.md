# Phase 4 Evaluation — Application Orchestrator

**Goal:** `get_recommendations()` end-to-end without UI.  
**Plan reference:** [implementation-plan.md](../implementation-plan.md) § Phase 4  
**Edge cases:** [edgecase.md](../edgecase.md) §5 (O-*), F-01, L-10–L-16

---

## Prerequisites

- Phases 1–3 PASS
- Mock `LLMClient` for automated tests; live key for manual CLI demo

---

## Automated evaluation

| # | Check | Command | Pass |
|---|--------|---------|------|
| A4-1 | Orchestrator tests | `pytest tests/test_recommender.py -q` | All pass |
| A4-2 | Mock LLM E2E | Full `RecommendationResponse` shape | Pass |
| A4-3 | Empty filter | Mock store/filter → no LLM call invoked | O-01 |
| A4-4 | Merge integrity | `name`, `rating`, `cost` match store not mock LLM text | O-16 |
| A4-5 | Invalid preferences | Raises validation error before filter | Pass |

---

## Manual evaluation (CLI)

| # | Criterion | Steps | Pass |
|---|-----------|-------|------|
| M4-1 | Happy path JSON | CLI: Bangalore, medium, Italian, min 4.0 | 1–5 items + summary |
| M4-2 | Response fields | Each item has name, cuisines, rating, cost, explanation, rank | All present |
| M4-3 | Meta | `candidates_considered` present and ≤ MAX | Pass |
| M4-4 | Empty path | Nonexistent city | Empty list, message, no LLM billed |
| M4-5 | Display vs LLM | Compare `name` in JSON to store by id | Exact match |

---

## Blocker criteria

- [ ] **B4-1** `get_recommendations` returns `RecommendationResponse` without UI.
- [ ] **B4-2** Zero filter matches → no LLM invocation (O-01, F-01).
- [ ] **B4-3** Structured fields from store; explanations from LLM only (O-16, L-16).
- [ ] **B4-4** Invalid preferences → clear error, no partial response.
- [ ] **B4-5** LLM failure after retry → user-safe error (O-06).

---

## Important criteria

- [ ] **I4-1** Partial valid LLM ids → return valid subset (O-03).
- [ ] **I4-2** Logging: filter count, LLM latency (architecture §9).
- [ ] **I4-3** `preferences_used` reflects coerced values (O-07).

---

## Sample CLI preferences (JSON)

```json
{
  "location": "Bangalore",
  "budget": "medium",
  "cuisine": "Italian",
  "min_rating": 4.0,
  "additional_preferences": ["family-friendly"],
  "top_k": 5
}
```

---

## Artifacts to demo

- CLI stdout JSON for happy path + empty path
- `tests/test_recommender.py` with mocked LLM

---

## Phase gate

**PASS** → Phase 5 when blockers + A4-1 + M4-1 + M4-4 pass.
