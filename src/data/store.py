"""In-memory restaurant store with optional parquet cache (Phase 1)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.config import get_settings
from src.data.loader import DatasetLoadError, load_raw_dataset
from src.data.preprocessor import preprocess_rows
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

_store_instance: Optional["RestaurantStore"] = None


def _restaurants_from_dataframe(frame: pd.DataFrame) -> list[Restaurant]:
    """Rebuild Restaurant models from parquet, coercing NaN to None (D-16)."""
    records = frame.to_dict(orient="records")
    restaurants: list[Restaurant] = []
    for rec in records:
        for key in ("rating", "cost_for_two"):
            value = rec.get(key)
            if value is not None and pd.isna(value):
                rec[key] = None
        tier = rec.get("budget_tier")
        if tier is not None and pd.isna(tier):
            rec["budget_tier"] = None
        if "attributes_json" in rec:
            raw_attrs = rec.pop("attributes_json")
            if raw_attrs is None or (isinstance(raw_attrs, float) and pd.isna(raw_attrs)):
                rec["attributes"] = {}
            else:
                rec["attributes"] = json.loads(raw_attrs)
        restaurants.append(Restaurant.model_validate(rec))
    return restaurants


def _records_for_parquet(restaurants: list[Restaurant]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for restaurant in restaurants:
        payload = restaurant.model_dump(mode="json")
        payload["attributes_json"] = json.dumps(payload.pop("attributes", {}) or {})
        records.append(payload)
    return records


class RestaurantStore:
    """Read-only in-memory store of preprocessed restaurants."""

    def __init__(self) -> None:
        self._restaurants: list[Restaurant] = []
        self._by_id: dict[str, Restaurant] = {}
        self._loaded = False

    def load(self, *, force_refresh: bool = False) -> None:
        """Load from cache if configured, else HF → preprocess → optional cache write."""
        if self._loaded and not force_refresh:
            return

        cache_path = get_settings().data_cache_path
        if cache_path and cache_path.exists() and not force_refresh:
            try:
                self._load_from_cache(cache_path)
                self._loaded = True
                logger.info(
                    "Loaded %s restaurants from cache %s",
                    len(self._restaurants),
                    cache_path,
                )
                return
            except Exception as exc:
                logger.warning(
                    "Cache file unreadable (%s); reprocessing from source: %s",
                    cache_path,
                    exc,
                )

        raw_rows = load_raw_dataset()
        result = preprocess_rows(raw_rows)
        if result.stats.accepted == 0:
            raise DatasetLoadError(
                "Preprocessing produced zero restaurants. "
                "Check dataset mapping in src/data/preprocessor.py."
            )

        self._set_restaurants(result.restaurants)
        self._loaded = True
        logger.info(
            "Loaded %s restaurants from Hugging Face (skipped %s rows)",
            len(self._restaurants),
            result.stats.skipped,
        )

        if cache_path:
            self._write_cache(cache_path)

    def _set_restaurants(self, restaurants: list[Restaurant]) -> None:
        self._restaurants = restaurants
        self._by_id = {r.id: r for r in restaurants}

    def _load_from_cache(self, path: Path) -> None:
        frame = pd.read_parquet(path)
        if frame.empty:
            raise ValueError("Cache parquet is empty")
        restaurants = _restaurants_from_dataframe(frame)
        self._set_restaurants(restaurants)

    def _write_cache(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(_records_for_parquet(self._restaurants))
        # Parquet/pandas use NaN for missing scalars; keep JSON-null semantics on read.
        frame = frame.astype(object).where(pd.notnull(frame), None)
        frame.to_parquet(path, index=False)
        logger.info("Wrote %s restaurants to cache %s", len(self._restaurants), path)

    def get_all(self) -> list[Restaurant]:
        if not self._loaded:
            self.load()
        return list(self._restaurants)

    def get_by_id(self, restaurant_id: str) -> Optional[Restaurant]:
        if not self._loaded:
            self.load()
        return self._by_id.get(restaurant_id)

    def count_by_location(self, location: str) -> int:
        needle = location.strip().lower()
        return sum(1 for r in self.get_all() if r.location_key == needle or needle in r.location_key)


def get_store() -> RestaurantStore:
    """Module-level singleton loaded at first use."""
    global _store_instance
    if _store_instance is None:
        _store_instance = RestaurantStore()
        _store_instance.load()
    return _store_instance


def reset_store() -> None:
    """Clear singleton (for tests)."""
    global _store_instance
    _store_instance = None
