# Edge Cases — Restaurant Recommendation System

Catalog of edge cases for implementation and testing, derived from [architecture.md](./architecture.md) §8 and [implementation-plan.md](./implementation-plan.md). Each item lists **expected behavior**, **primary phase** to handle, and **how to verify**.

**Legend:** P0–P6 = implementation phases. **Severity:** `blocker` (must handle in v1), `important` (should handle), `minor` (document or defer).

---

## 1. Data ingestion & preprocessing (Phase 1)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| D-01 | Hugging Face download fails (network, 403, timeout) | Fail startup with clear message; retry guidance; use `DATA_CACHE_PATH` if file exists | blocker | Disconnect network; run with/without cache |
| D-02 | Dataset empty or split missing | Startup error; do not run with zero restaurants | blocker | Mock empty dataset |
| D-03 | Column names differ from mapper assumptions | Preprocessor maps known aliases or fails loudly at load with column list | blocker | Inspect raw schema in Phase 1 exploration |
| D-04 | Missing `name` or `location` | Skip row or assign default per policy; log count of skipped rows | important | Fixture row with null name |
| D-05 | Missing rating | Exclude from rating-based filters or treat as 0; document policy | important | Row with null rating |
| D-06 | Missing `cost_for_two` | `budget_tier` null; exclude from budget filter or treat as unknown | important | Filter medium budget → row not returned |
| D-07 | Non-numeric rating/cost (`"4.1/5"`, `"₹800"`) | Parse best-effort or skip row; no crash | blocker | Unit test parser helpers |
| D-08 | Rating out of range (e.g. 6.0, negative) | Clamp or reject row | important | Fixture invalid rating |
| D-09 | Cost = 0 or extremely high outlier | Assign tier by thresholds; optional cap/winsorize | minor | Distribution review |
| D-10 | Duplicate restaurant names same city | Stable unique `id` (index/hash); both may appear in results | important | Two rows same name |
| D-11 | Cuisine string empty or only commas | `cuisines = []`; cuisine filter may exclude | important | `",,"` cuisine field |
| D-12 | Multi-cuisine string (`"Chinese, Italian, Fast Food"`) | Split, trim, case-normalize tokens | blocker | Assert list length > 1 |
| D-13 | Location inconsistent casing (`"bangalore"` vs `"Bangalore"`) | Compare normalized; display original or canonical | blocker | Filter with different casing |
| D-14 | Location typos / abbreviations (`"Bengaluru"` vs `"Bangalore"`) | v1: exact/contains match only; no fuzzy unless added | minor | Document unsupported |
| D-15 | Special characters in name/cuisine (unicode, `&`) | Preserve in display; JSON-safe in prompts | important | Unicode name in UI |
| D-16 | Corrupt cache file (partial parquet) | Delete or ignore cache; re-download/reprocess | important | Truncate cache file |
| D-17 | Cache stale after dataset version change | Optional version key in cache filename | minor | Change `HF_DATASET_NAME` |
| D-18 | Very large dataset (memory pressure) | Load once; optional sampling for dev only (document) | minor | Monitor memory at startup |

---

## 2. User preferences & validation (Phase 2, UI Phase 5)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| P-01 | Empty `location` | Validation error before filter | blocker | Submit empty form |
| P-02 | Whitespace-only location (`"   "`) | Reject as empty | blocker | Trim validator |
| P-03 | Invalid `budget` (typo, number) | Pydantic validation error | blocker | API invalid enum |
| P-04 | `min_rating` > 5 or < 0 | Validation error | blocker | `min_rating=6` |
| P-05 | `min_rating` omitted | No rating filter applied | important | None vs 0 |
| P-06 | `cuisine` omitted | No cuisine filter; all cuisines in location+budget | important | Optional field |
| P-07 | `cuisine` with no matches in city | Empty filter result; no LLM | blocker | Obscure cuisine |
| P-08 | `top_k` = 0 or negative | Validation error or coerce to 1 | important | `top_k=0` |
| P-09 | `top_k` > max cap (e.g. 100) | Coerce to max (10) | important | `top_k=50` |
| P-10 | `additional_preferences` empty list | Omit from prompt or pass empty | minor | `[]` |
| P-11 | Very long additional preference strings | Truncate in prompt or reject length | minor | 10k char string |
| P-12 | SQL/injection-style input in location | Treated as literal string; no eval | important | `"; DROP TABLE` |
| P-13 | Location not in dataset (`"Tokyo"`) | Zero candidates; user message | blocker | Unknown city |
| P-14 | Budget tier has zero restaurants in city | Zero candidates | blocker | low budget rare city |
| P-15 | Conflicting soft prefs (`"quiet"` + `"lively"`) | LLM may still rank; no crash | minor | Manual LLM test |

---

## 3. Filtering & candidates (Phase 2)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| F-01 | Zero matches after all filters | `FilterResult` empty + message; **no LLM call** (Phase 4) | blocker | Strict prefs |
| F-02 | Exactly one match | Return 1 candidate; LLM may return 1 recommendation | important | Single row city |
| F-03 | Thousands of matches in city | Truncate to `MAX_CANDIDATES_FOR_LLM` by rating desc, then name | blocker | Bangalore + broad filters |
| F-04 | Tie on rating when truncating | Stable secondary sort by name/id | important | Equal ratings |
| F-05 | Cuisine substring false positive (`"Indian"` matches `"South Indian"`) | Document as acceptable contains match or use token match | minor | Policy test |
| F-06 | User cuisine case (`"italian"` vs `"Italian"`) | Case-insensitive match | blocker | Lowercase input |
| F-07 | `min_rating` excludes all (4.9 in low-rated set) | Empty result | blocker | High min_rating |
| F-08 | Restaurant missing `budget_tier` | Excluded when user selected budget | important | D-06 + filter |
| F-09 | Restaurant rating exactly equals `min_rating` | Included (`>=`) | important | Boundary 4.0 |
| F-10 | Filter order performance (huge city list) | Location first; acceptable latency | minor | Log timing |
| F-11 | Candidate payload huge (30 restaurants × fields) | Stay under token budget; minimal fields only | important | Prompt size check |

---

## 4. LLM integration (Phase 3)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| L-01 | Missing `LLM_API_KEY` | Clear error when invoking LLM; app may start if data-only | blocker | Run without key |
| L-02 | Invalid API key (401) | User-safe error; no key in message | blocker | Wrong key |
| L-03 | LLM timeout (>30s) | Retry once; then graceful failure | blocker | Mock slow client |
| L-04 | Rate limit (429) | Backoff retry; then error | important | Mock 429 |
| L-05 | Empty model response | Parse failure → retry or error | blocker | Mock `""` |
| L-06 | Non-JSON response (prose only) | Parser fails; one retry with “JSON only” | blocker | Fixture prose |
| L-07 | JSON wrapped in markdown fences | Strip fences; parse | blocker | ` ```json ... ``` ` |
| L-08 | Malformed JSON (trailing comma) | Parse fail → retry/error | important | Broken fixture |
| L-09 | Valid JSON but wrong schema (missing `recommendations`) | Validation error | blocker | Partial schema |
| L-10 | `restaurant_id` not in candidate list | Reject row; log warning | blocker | Unknown id in response |
| L-11 | Duplicate `restaurant_id` in LLM output | Dedupe by id; keep best rank | important | Duplicate ids |
| L-12 | Duplicate ranks (two `rank: 1`) | Re-sort by rank or renumber | important | Fixture |
| L-13 | Fewer than `top_k` recommendations returned | Return what LLM gave if valid | important | top_k=5, got 2 |
| L-14 | More than `top_k` in response | Truncate to top_k by rank | important | 10 items, top_k=5 |
| L-15 | LLM invents restaurant not in list | Parser drops; if all invalid → error | blocker | Fake id |
| L-16 | LLM copies wrong name in explanation only | UI uses store for name/rating/cost | blocker | Mismatch explanation |
| L-17 | Empty `summary` | Optional; UI hides or shows default | minor | Null summary |
| L-18 | Very long explanations | Display full or truncate in UI with expand | minor | Long text |
| L-19 | Single candidate; LLM returns wrong id | At least one valid or error | important | 1 candidate test |
| L-20 | Token limit exceeded (prompt too large) | Reduce MAX or truncate candidates earlier | important | Max candidates edge |

---

## 5. Orchestrator & merge (Phase 4)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| O-01 | Filter empty → orchestrator called | Skip LLM; return empty recommendations + message | blocker | Integration test |
| O-02 | LLM success but all ids invalid | Error after parse; no partial fake data | blocker | Mock bad ids |
| O-03 | LLM returns subset of valid ids | Return valid merged rows only | important | 3 of 5 valid |
| O-04 | `restaurant_id` valid but id removed from store (race) | Should not happen v1; handle KeyError gracefully | minor | — |
| O-05 | Concurrent requests (Streamlit double-click) | Two LLM calls; UI shows latest or disable button while loading | important | Double submit |
| O-06 | Partial LLM failure after retry | User-safe error; no half-populated corrupt response | blocker | Mock fail twice |
| O-07 | `preferences_used` echo in response | Matches input after coercion (top_k cap) | minor | Inspect JSON |
| O-08 | Meta `candidates_considered` | Equals post-truncation count sent to LLM | important | Log vs meta |

---

## 6. Presentation layer (Phase 5)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| U-01 | App started before store load completes | Loading indicator; block submit until ready | important | Slow cache |
| U-02 | Store load failed at startup | Error page; instructions to fix cache/network | blocker | Break loader |
| U-03 | Submit with invalid form | Inline validation; no API call | blocker | Empty location |
| U-04 | LLM slow | Spinner/skeleton; no duplicate submits | important | Long request |
| U-05 | Zero results UI | Empty state message; not blank screen | blocker | Tokyo location |
| U-06 | API key missing on submit | Actionable error (configure `.env`) | blocker | No key |
| U-07 | Browser refresh mid-request | New session; no stale partial results required | minor | Refresh |
| U-08 | Very long result list (top_k=10) | Scrollable layout; readable cards | minor | max top_k |
| U-09 | Cost displayed as null | Show “N/A” or hide cost field | important | D-06 row in results* |

\*Only if such row could appear after filter policy allows it.

---

## 7. Configuration & environment (Phase 0+)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| C-01 | Missing `.env` file | Defaults where safe; fail on required LLM vars at call time | important | No .env |
| C-02 | Invalid `MAX_CANDIDATES_FOR_LLM` (non-int) | Config error at startup | important | `MAX=abc` |
| C-03 | `MAX_CANDIDATES_FOR_LLM` = 0 or negative | Coerce to sensible default (e.g. 20) | important | `MAX=0` |
| C-04 | Wrong `HF_DATASET_NAME` | Load error with dataset id in message | blocker | Bad name |
| C-05 | Secrets committed to git | Prevent via `.gitignore`; document | blocker | Repo scan |

---

## 8. End-to-end & cross-cutting (Phase 6)

| ID | Edge case | Expected behavior | Severity | Verify |
|----|-----------|-------------------|----------|--------|
| E-01 | Same preferences twice | Deterministic filter set; LLM may vary slightly | minor | Repeat submit |
| E-02 | User changes only `additional_preferences` | Same hard filter set; LLM narrative may change | important | A/B submit |
| E-03 | All filters match exactly `top_k` candidates | No truncation; LLM ranks all | important | Tight filter |
| E-04 | Offline demo without LLM | Mock client returns fixtures; UI still works | important | CI / grading |
| E-05 | Logging contains no API keys | Redact in logs | blocker | Log inspection |
| E-06 | P95 latency > 15s | Document; optimize MAX or model | minor | Timing |

---

## 9. Out of scope (document, do not implement in v1)

| ID | Edge case | v1 stance |
|----|-----------|-----------|
| X-01 | Real-time table availability | Not supported |
| X-02 | User accounts / history | Not supported |
| X-03 | Fuzzy city alias resolution | Not supported unless added |
| X-04 | Multi-city comparison in one request | Not supported |
| X-05 | Adversarial prompt injection changing filters | Filters are code-side only; LLM cannot widen candidate set |

---

## 10. Edge case → phase matrix

| Phase | Primary edge-case IDs |
|-------|------------------------|
| 0 | C-01–C-05 |
| 1 | D-01–D-18 |
| 2 | P-01–P-15, F-01–F-11 |
| 3 | L-01–L-20 |
| 4 | O-01–O-08, F-01, L-10–L-16 |
| 5 | U-01–U-09, P-01–P-03 |
| 6 | All blockers regression-tested |

---

## 11. Recommended test fixtures

Create under `tests/fixtures/`:

| File | Covers |
|------|--------|
| `restaurants_minimal.json` | 5–10 synthetic restaurants for filter/parser tests |
| `llm_valid_response.json` | Valid LLM schema |
| `llm_fenced_json.txt` | L-07 |
| `llm_invalid_ids.json` | L-10, O-02 |
| `llm_prose_only.txt` | L-06 |

---

## References

- [architecture.md](./architecture.md) — §7 algorithms, §8 error handling
- [implementation-plan.md](./implementation-plan.md) — phase tasks and risks
- [eval.md](./eval.md) — per-phase evaluation criteria
