# Deployment Plan — Zomato AI Restaurant Recommendations on Streamlit Community Cloud

## Overview

Deploy the Streamlit-based restaurant recommendation app to **Streamlit Community Cloud** (free tier). The app uses a HuggingFace dataset for data, Groq (LLaMA 3.3 70B) for LLM-powered ranking, and Streamlit for the UI.

---

## Task 1: Prepare the Repository for Deployment

### 1.1 Create `streamlit_app.py` (entry point)

Streamlit Community Cloud expects a single entry-point script at the repo root. Create a thin wrapper:

```python
# streamlit_app.py
from src.main import run

run()
```

### 1.2 Verify `requirements.txt`

The existing `requirements.txt` already lists all runtime dependencies. Ensure these are pinned or bounded correctly:

```
datasets>=2.18.0
pandas>=2.2.0
pyarrow>=15.0.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
python-dotenv>=1.0.0
streamlit>=1.32.0
openai>=1.14.0
```

> Remove dev/test dependencies (`pytest`) from the deployment requirements, or move them to a separate `requirements-dev.txt`.

### 1.3 Create `packages.txt` (if needed)

If any system-level packages are required (e.g., `build-essential`), list them here. For this project, it is likely empty or not needed.

---

## Task 2: Configure Secrets on Streamlit Cloud

Streamlit Community Cloud does **not** use `.env` files. All environment variables must be added via **App Settings → Secrets**.

Add the following secrets in the Streamlit Cloud dashboard:

```toml
# .streamlit/secrets.toml  (local testing equivalent)

HF_DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"
LLM_PROVIDER = "groq"
LLM_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxx"
LLM_MODEL = "llama-3.3-70b-versatile"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
MAX_CANDIDATES_FOR_LLM = "25"
```

> **Important:** Never commit real API keys to the repo. Use the Streamlit Cloud dashboard to set secrets in production.

### Mapping from `.env` variables to Streamlit Secrets

| `.env` Variable              | Streamlit Secret Key       | Required |
| ---------------------------- | -------------------------- | -------- |
| `LLM_API_KEY`               | `LLM_API_KEY`             | Yes      |
| `HF_DATASET_NAME`           | `HF_DATASET_NAME`         | No (has default) |
| `LLM_PROVIDER`              | `LLM_PROVIDER`            | No (has default) |
| `LLM_MODEL`                 | `LLM_MODEL`               | No (has default) |
| `LLM_BASE_URL`              | `LLM_BASE_URL`            | No (has default) |
| `MAX_CANDIDATES_FOR_LLM`    | `MAX_CANDIDATES_FOR_LLM`  | No (has default) |
| `DATA_CACHE_PATH`           | —                          | No (not needed on cloud) |

---

## Task 3: Update `src/config.py` for Streamlit Secrets Compatibility

Streamlit injects secrets as environment variables automatically, so `pydantic-settings` will pick them up without code changes. However, verify:

1. `SettingsConfigDict(env_file=".env")` — this is fine; on cloud, `.env` won't exist, and env vars / secrets take precedence.
2. All fields use `validation_alias` matching the secret key names (already done).

**No code changes required** — the existing config is compatible.

---

## Task 4: Handle Dataset Caching on Streamlit Cloud

The app loads the Zomato dataset from HuggingFace via `datasets` library and caches a preprocessed Parquet file.

### Strategy

| Concern              | Approach |
| -------------------- | -------- |
| First-load latency   | The `datasets` library downloads and caches to `~/.cache/huggingface/`. Streamlit Cloud persists this across sessions. |
| Preprocessed Parquet | Store in `data/processed/restaurants.parquet` and commit to Git (already exists). Set `DATA_CACHE_PATH` to this path to skip HF download entirely. |
| Memory               | The Parquet file is loaded once and cached via `@st.cache_resource`. |

**Recommended:** Commit the preprocessed `restaurants.parquet` to the repo and set:

```toml
DATA_CACHE_PATH = "data/processed/restaurants.parquet"
```

This avoids the HuggingFace download on every cold start.

---

## Task 5: Deploy to Streamlit Community Cloud

### 5.1 Push code to GitHub

```bash
git add streamlit_app.py requirements.txt
git commit -m "Add Streamlit Cloud deployment entry point"
git push origin main
```

### 5.2 Create the app on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New App**
3. Fill in:
   - **Repository:** `your-username/ZOMATO`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App name:** `zomato-ai-recommendations` (or your choice)
4. Click **Advanced Settings** and paste the secrets from Task 2
5. Click **Deploy**

### 5.3 Post-deployment checks

- [ ] App loads without errors
- [ ] Sidebar shows restaurant count and "Groq API key: Configured"
- [ ] Submit a preference form and verify recommendations are returned
- [ ] Verify Groq latency is displayed in the metadata line
- [ ] Test with invalid inputs to confirm error handling works

---

## Task 6: Optional Enhancements

| Enhancement                     | Description |
| ------------------------------- | ----------- |
| **Custom domain**               | Streamlit Cloud provides `appname.streamlit.app`. A custom domain can be configured in settings. |
| **Resource limits**             | Free tier: 1 GB RAM. Monitor usage; reduce `MAX_CANDIDATES_FOR_LLM` if OOM occurs. |
| **Sleep/hibernation**           | Free apps sleep after 7 days of inactivity. First request after sleep has a cold-start delay (~30-60s). |
| **Analytics**                   | Enable Streamlit's built-in usage analytics in app settings. |
| **Pre-warm cache**              | Add a startup hook that calls `_cached_store()` to pre-load data on boot. |

---

## File Changes Summary

| File                  | Action   | Purpose |
| --------------------- | -------- | ------- |
| `streamlit_app.py`    | Create   | Entry point for Streamlit Cloud |
| `requirements.txt`    | Modify   | Remove dev deps or split into `requirements-dev.txt` |
| `.streamlit/secrets.toml` | Create (local only) | Local secret values for testing |
| `.gitignore`          | Update   | Add `.streamlit/secrets.toml` to prevent committing secrets |
