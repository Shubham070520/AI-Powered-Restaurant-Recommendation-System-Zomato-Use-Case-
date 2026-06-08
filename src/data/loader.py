"""Load raw restaurant records from Hugging Face (Phase 1)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Iterator

from datasets import load_dataset
from datasets.exceptions import DatasetsError

from src.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_SPLIT = "train"


class DatasetLoadError(RuntimeError):
    """Raised when the Hugging Face dataset cannot be loaded (D-01, D-02)."""


def _validate_raw_columns(column_names: list[str]) -> None:
    """Fail loudly if expected columns are missing (D-03)."""
    required = {"name", "address", "cuisines", "approx_cost(for two people)", "rate"}
    missing = required - set(column_names)
    if missing:
        raise DatasetLoadError(
            f"Dataset schema mismatch. Missing columns: {sorted(missing)}. "
            f"Found: {column_names}. Update preprocessor mapping in src/data/preprocessor.py."
        )


def load_raw_dataset(
    *,
    dataset_name: str | None = None,
    split: str = DEFAULT_SPLIT,
) -> Iterable[dict]:
    """
    Load raw rows from Hugging Face.

    Yields dict rows for the preprocessor. Does not use DATA_CACHE_PATH;
    use RestaurantStore for processed parquet cache.
    """
    name = dataset_name or get_settings().hf_dataset_name
    try:
        dataset = load_dataset(name, split=split)
    except DatasetsError as exc:
        raise DatasetLoadError(
            f"Failed to download or load dataset '{name}' (split={split}). "
            "Check your network connection and HF_DATASET_NAME. "
            "If you have a preprocessed cache, set DATA_CACHE_PATH to skip download."
        ) from exc
    except Exception as exc:
        raise DatasetLoadError(
            f"Failed to load dataset '{name}' (split={split}): {exc}"
        ) from exc

    if len(dataset) == 0:
        raise DatasetLoadError(
            f"Dataset '{name}' split '{split}' is empty. Cannot start with zero restaurants."
        )

    _validate_raw_columns(dataset.column_names)
    logger.info("Loaded raw dataset '%s' with %s rows", name, len(dataset))
    return (dict(row) for row in dataset)


def iter_raw_from_parquet(path: Path) -> Iterator[dict]:
    """Optional: load raw-like rows from a saved parquet (processed cache)."""
    import pandas as pd

    frame = pd.read_parquet(path)
    for row in frame.to_dict(orient="records"):
        yield row


def smoke_report() -> None:
    """Load store and print summary for Phase 1 milestone demo."""
    from collections import Counter

    from src.data.store import get_store

    store = get_store()
    restaurants = store.get_all()
    n = len(restaurants)
    if n == 0:
        raise SystemExit("No restaurants loaded.")

    city_counts = Counter(r.location for r in restaurants)
    cuisine_tokens: Counter[str] = Counter()
    for r in restaurants:
        cuisine_tokens.update(r.cuisines)

    top_cities = city_counts.most_common(5)
    top_cuisines = cuisine_tokens.most_common(8)

    print(f"Loaded {n} restaurants")
    for city, count in top_cities:
        print(f"  {city}: {count}")
    cuisine_summary = ", ".join(f"{c} ({cnt})" for c, cnt in top_cuisines[:5])
    print(f"Top cuisines: {cuisine_summary}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    smoke_report()
