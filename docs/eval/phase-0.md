# Phase 0 Evaluation — Project Foundation

**Goal:** Runnable repo, dependencies, configuration, folder layout.  
**Plan reference:** [implementation-plan.md](../implementation-plan.md) § Phase 0  
**Edge cases:** [edgecase.md](../edgecase.md) §7 (C-01–C-05)

---

## Prerequisites

- Python 3.11+ installed
- Git repo initialized (optional)

---

## Automated evaluation

| # | Check | Command / action | Pass |
|---|--------|------------------|------|
| A0-1 | Dependencies install | `pip install -r requirements.txt` | No errors |
| A0-2 | Config import | `python -c "from src.config import settings"` | No import error |
| A0-3 | Required paths exist | `src/`, `src/config.py`, `.env.example`, `.gitignore` | All present |
| A0-4 | Secrets ignored | `.env` listed in `.gitignore` | Yes |

---

## Manual evaluation

| # | Criterion | Steps | Pass |
|---|-----------|-------|------|
| M0-1 | README documents setup | Read `README.md` for venv, install, env vars | Clear enough for new developer |
| M0-2 | UI choice documented | README states Streamlit or FastAPI | Explicit |
| M0-3 | Missing LLM key behavior | Start without `LLM_API_KEY` (if validated at import, document) | No crash on import-only; clear when LLM needed later |
| M0-4 | `.env.example` complete | Compare to architecture config table | `HF_DATASET_NAME`, `LLM_*`, `MAX_CANDIDATES_FOR_LLM` |

---

## Blocker criteria (must pass)

- [ ] **B0-1** Clean install in fresh venv succeeds.
- [ ] **B0-2** `src/config.py` reads environment with documented defaults.
- [ ] **B0-3** `.env` and `data/processed/` are gitignored.
- [ ] **B0-4** Folder layout matches architecture §6 (or documented deviation).

---

## Important criteria (should pass)

- [ ] **I0-1** Invalid env values fail fast with readable message (C-02, C-03) if validated in Phase 0.
- [ ] **I0-2** README lists all required env vars.

---

## Artifacts to submit / demo

- `requirements.txt`, `.env.example`, `src/config.py`, `README.md` (partial)

---

## Phase gate

**PASS** → Proceed to Phase 1 when all **blocker** items checked.
