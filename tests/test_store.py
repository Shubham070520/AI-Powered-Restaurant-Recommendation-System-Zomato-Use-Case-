"""Restaurant store and cache tests (Phase 1)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.preprocessor import preprocess_rows
from src.data.store import RestaurantStore, _restaurants_from_dataframe
from src.models.restaurant import BudgetTier, Restaurant


def _minimal_restaurant() -> Restaurant:
    return Restaurant(
        id="r_test",
        name="Cache Test",
        location="Bangalore",
        cuisines=["Italian"],
        rating=None,
        cost_for_two=None,
        budget_tier=None,
        attributes={},
    )


def test_parquet_round_trip_preserves_nulls(tmp_path: Path) -> None:
    store = RestaurantStore()
    store._set_restaurants([_minimal_restaurant()])
    cache_file = tmp_path / "restaurants.parquet"
    store._write_cache(cache_file)

    frame = pd.read_parquet(cache_file)
    loaded = _restaurants_from_dataframe(frame)
    assert len(loaded) == 1
    assert loaded[0].cost_for_two is None
    assert loaded[0].budget_tier is None


def test_store_load_from_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "url": "https://example.com/a",
            "name": "A",
            "address": "Street, Bangalore",
            "cuisines": "Italian",
            "rate": "4.0/5",
            "approx_cost(for two people)": "400",
        }
    ]
    restaurants = preprocess_rows(rows).restaurants
    cache_file = tmp_path / "restaurants.parquet"
    from src.data.store import _records_for_parquet

    frame = pd.DataFrame(_records_for_parquet(restaurants))
    frame = frame.astype(object).where(pd.notnull(frame), None)
    frame.to_parquet(cache_file, index=False)

    monkeypatch.setenv("DATA_CACHE_PATH", str(cache_file))
    from src.config import get_settings

    get_settings.cache_clear()

    store = RestaurantStore()
    store.load()
    assert len(store.get_all()) == 1
    assert store.get_by_id(restaurants[0].id) is not None
    assert store.get_all()[0].budget_tier == BudgetTier.LOW

    get_settings.cache_clear()
