# Phase 6 Evaluation — Hardening & Delivery (v1 Complete)

**Goal:** Meet project success criteria; repo ready for review or submission.  
**Plan reference:** [implementation-plan.md](../implementation-plan.md) § Phase 6  
**Edge cases:** [edgecase.md](../edgecase.md) §8–10 (E-*, full blocker regression)

---

## Prerequisites

- Phase 5 PASS

---

## Automated evaluation

| # | Check | Command | Pass |
|---|--------|---------|------|
| A6-1 | Full test suite | `pytest tests/ -q` | All pass |
| A6-2 | Required test modules exist | `test_preprocessor`, `test_filters`, `test_parser`, `test_recommender` | Present |
| A6-3 | Mock LLM in CI | Recommender tests run without network | Pass |
| A6-4 | No secrets in repo | `git grep -i api_key` / manual review | No real keys |

---

## Edge-case regression (blockers)

Verify each **blocker** in [edgecase.md](../edgecase.md) for the implemented phase:

| Area | IDs | Method |
|------|-----|--------|
| Data | D-01, D-07, D-12, D-13 | Tests + smoke |
| Preferences | P-01, P-03, P-13 | Tests + UI |
| Filters | F-01, F-03 | Tests + CLI |
| LLM | L-07, L-10, L-15 | Parser tests |
| Orchestrator | O-01, O-16 | Integration test |
| UI | U-05, U-06 | Manual |
| Security | E-05, C-05 | Log + git review |

---

## Manual evaluation — project success

| # | Criterion | Verification | Pass |
|---|-----------|--------------|------|
| M6-1 | Candidates reduced before LLM | Check `meta.candidates_considered` vs city total | Smaller |
| M6-2 | Hard constraints honored | Spot-check 5 results vs filters | 5/5 match |
| M6-3 | Explanations preference-aware | Read 3 explanations | Mention prefs |
| M6-4 | End-to-end from README | Reviewer script | &lt; 15 min setup |
| M6-5 | Error handling audit | architecture §8 table | Each row tested |
| M6-6 | Demo scenarios | 3–5 scenarios documented | Optional `demo-scenarios.md` |

---

## Prompt quality review (manual)

Run at least **3** real preference sets; for each:

| Check | Pass |
|-------|------|
| Rankings plausible vs rating/cuisine | Subjective OK |
| No restaurant outside candidate set | Required |
| Explanations not generic boilerplate only | Subjective OK |

---

## Blocker criteria (Definition of Done)

- [ ] **B6-1** All Phase 0–5 blockers still pass (regression).
- [ ] **B6-2** `pytest tests/` green.
- [ ] **B6-3** Live demo: form → recommendations with explanations.
- [ ] **B6-4** README: setup, env, run, troubleshooting (HF, API key, empty city).
- [ ] **B6-5** Out-of-scope not started (accounts, live Zomato API, payments).
- [ ] **B6-6** problemStatement success criteria 1–4 evidenced (see [eval.md](../eval.md)).

---

## Important criteria

- [ ] **I6-1** Budget thresholds tuned to dataset distribution.
- [ ] **I6-2** `MAX_CANDIDATES_FOR_LLM` tuned (latency + cost).
- [ ] **I6-3** Optional Makefile/scripts for `test` and `run`.
- [ ] **I6-4** P95 latency documented if &gt; 15s (E-06).

---

## Submission package checklist

- [ ] Source code under `src/`
- [ ] `requirements.txt`, `.env.example`
- [ ] `README.md` with run instructions
- [ ] `docs/problemStatement.md`, `architecture.md`, `implementation-plan.md`
- [ ] `docs/edgecase.md`, `docs/eval.md`
- [ ] Tests under `tests/`
- [ ] Demo screenshot or recording (recommended)

---

## Phase gate (project v1)

**PASS** → Project v1 complete when all **B6-*** blockers checked and eval.md project-level table satisfied.

---

## Post-v1 (not required for PASS)

- Phase 7+ items in implementation-plan (FastAPI SPA, embeddings, caching) — evaluate separately when started.
