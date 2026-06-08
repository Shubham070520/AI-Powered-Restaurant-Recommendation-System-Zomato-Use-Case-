# Evaluation Guide — Phase-Wise Criteria

How to evaluate each implementation phase before moving to the next. Detailed checklists live in [eval/](./eval/).

| Phase | Document | Gate summary |
|-------|----------|--------------|
| 0 | [eval/phase-0.md](./eval/phase-0.md) | Repo installs; config loads |
| 1 | [eval/phase-1.md](./eval/phase-1.md) | Dataset → clean `Restaurant` store |
| 2 | [eval/phase-2.md](./eval/phase-2.md) | Preferences validate; filters correct |
| 3 | [eval/phase-3.md](./eval/phase-3.md) | LLM prompt/parse reliable |
| 4 | [eval/phase-4.md](./eval/phase-4.md) | Orchestrator E2E without UI |
| 5 | [eval/phase-5.md](./eval/phase-5.md) | UI demo complete |
| 6 | [eval/phase-6.md](./eval/phase-6.md) | Production-ready v1 / submission |

**Related:** [edgecase.md](./edgecase.md) — edge cases to test per phase.

---

## Evaluation process (all phases)

1. Complete implementation tasks in [implementation-plan.md](./implementation-plan.md) for the phase.
2. Run **automated checks** (tests, smoke scripts) listed in the phase eval doc.
3. Run **manual scenarios** (minimum set in each phase doc).
4. Verify **phase edge cases** from [edgecase.md](./edgecase.md) for that phase’s IDs.
5. Mark phase **PASS** only if all **blocker** criteria pass; document known gaps for `important`/`minor`.

**PASS / FAIL:** A phase fails if any **blocker** criterion fails or a required artifact is missing.

---

## Project-level success (after Phase 6)

Aligned with [problemStatement.md](./problemStatement.md):

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Preferences reduce candidates before LLM | `meta.candidates_considered` in response; logs |
| 2 | Recommendations honor location, budget, cuisine, min rating | Spot-check + `test_filters` |
| 3 | Each result includes AI explanation | UI / JSON `explanation` |
| 4 | Display shows name, cuisine, rating, cost, explanation | UI screenshot or CLI JSON |
| 5 | End-to-end demo runnable from README | Reviewer runs app in &lt; 15 min |
| 6 | No invented restaurants in output | Parser + merge tests; manual id check |

---

## Quick regression suite (Phase 6+)

```text
pytest tests/ -q
# Manual: Bangalore, medium, Italian, min_rating=4.0 → 1–5 results with explanations
# Manual: location=NonexistentCity → empty state, no LLM charge
```

---

## References

- [implementation-plan.md](./implementation-plan.md)
- [architecture.md](./architecture.md)
- [edgecase.md](./edgecase.md)
