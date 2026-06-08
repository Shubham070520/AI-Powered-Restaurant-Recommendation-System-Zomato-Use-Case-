# AI-Powered Restaurant Recommendation System

Zomato-inspired restaurant recommendations combining structured filtering on a Hugging Face dataset with **Groq** LLM ranking and explanations.

**UI (v1):** [Streamlit](https://streamlit.io/) — see [docs/architecture.md](docs/architecture.md).

## Requirements

- Python 3.11+
- [Groq](https://console.groq.com/) API key for live recommendations

## Setup

```bash
cd ZOMATO
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
```

Edit `.env`:

- `LLM_API_KEY` — your Groq API key (required for live AI ranking)
- Optional: `DATA_CACHE_PATH=data/processed/restaurants.parquet` after first dataset load

## Run the app (Phase 5)

First launch downloads the Hugging Face dataset (~1–2 min) unless a cache file exists.

```bash
streamlit run src/main.py
```

Open the URL shown in the terminal (usually http://localhost:8501). Use the form to set location, budget, cuisine, and minimum rating, then click **Get recommendations**.

## CLI (Phase 4)

```bash
python -m src.services.recommend_cli --location Bangalore --budget medium --cuisine Italian --min-rating 4.0

# Or JSON file / stdin
python -m src.services.recommend_cli --json "{\"location\":\"Bangalore\",\"budget\":\"medium\",\"cuisine\":\"Italian\",\"min_rating\":4.0}"
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HF_DATASET_NAME` | No | `ManikaSaini/zomato-restaurant-recommendation` | Hugging Face dataset id |
| `DATA_CACHE_PATH` | No | — | Optional path to cached preprocessed data |
| `LLM_PROVIDER` | No | `groq` | LLM provider (`groq` for v1) |
| `LLM_API_KEY` | Live AI | — | Groq API key (never commit) |
| `LLM_MODEL` | No | `llama-3.3-70b-versatile` | Groq model id |
| `LLM_BASE_URL` | No | `https://api.groq.com/openai/v1` | Groq OpenAI-compatible endpoint |
| `LLM_TIMEOUT_SECONDS` | No | `30` | Request timeout |
| `MAX_CANDIDATES_FOR_LLM` | No | `25` | Max filtered restaurants sent to the LLM |

## Tests

```bash
python -m pytest tests/ -q
```

Mock LLM demo (no API key):

```bash
python -m src.llm.demo --mock
```

## Troubleshooting

| Issue | What to do |
|-------|------------|
| Dataset download slow/fails | Set `DATA_CACHE_PATH` after a successful load; check network |
| Missing API key | Add `LLM_API_KEY` to `.env` from [console.groq.com](https://console.groq.com/) |
| No matches | Try `Bangalore`, `medium` budget; dataset is mostly Bangalore |
| Groq rate limit | Wait and retry; reduce `MAX_CANDIDATES_FOR_LLM` |

## Project layout

```
src/
  main.py              # Streamlit UI
  config.py
  data/                # Dataset load & store
  domain/              # Filters & candidates
  llm/                 # Groq client, prompts, parser
  services/            # Orchestrator + CLI
  models/
tests/
docs/
```

## Documentation

- [Problem statement](docs/problemStatement.md)
- [Architecture](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Edge cases](docs/edgecase.md)
- [Evaluation](docs/eval.md)
