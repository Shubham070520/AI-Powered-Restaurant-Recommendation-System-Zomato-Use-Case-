"""Unit tests for dataset preprocessing (Phase 1)."""

from __future__ import annotations

import pytest

from src.data.preprocessor import (
    assign_budget_tier,
    extract_city,
    parse_cost,
    parse_rating,
    preprocess_rows,
    row_to_restaurant,
    split_cuisines,
)
from src.models.restaurant import BudgetTier


def _sample_row(**overrides: object) -> dict:
    base = {
        "url": "https://www.zomato.com/bangalore/test-restaurant",
        "name": "Test Bistro",
        "address": "1 MG Road, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "cuisines": "North Indian, Chinese",
        "rate": "4.2/5",
        "approx_cost(for two people)": "800",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Casual Dining",
    }
    base.update(overrides)
    return base


def test_split_cuisines_trims_tokens():
    assert split_cuisines("North Indian, Chinese, ") == [
        "North Indian",
        "Chinese",
    ]


def test_split_cuisines_empty():
    assert split_cuisines("") == []
    assert split_cuisines(",,") == []


def test_parse_rating_from_fraction():
    assert parse_rating("4.1/5") == 4.1


def test_parse_rating_missing():
    assert parse_rating("-") is None
    assert parse_rating("NEW") is None


def test_parse_rating_out_of_range():
    assert parse_rating("6.0/5") is None


def test_parse_cost_integer():
    assert parse_cost("800") == 800


def test_parse_cost_with_commas():
    assert parse_cost("1,200") == 1200


def test_parse_cost_range():
    assert parse_cost("300-400") == 350


def test_budget_tier_thresholds():
    assert assign_budget_tier(400) == BudgetTier.LOW
    assert assign_budget_tier(500) == BudgetTier.LOW
    assert assign_budget_tier(1200) == BudgetTier.MEDIUM
    assert assign_budget_tier(1501) == BudgetTier.HIGH
    assert assign_budget_tier(None) is None


def test_extract_city_bangalore_aliases():
    assert extract_city("Foo, Bengaluru") == "Bangalore"
    assert extract_city("Foo, Bangalore.") == "Bangalore"


def test_extract_city_case_insensitive_match_key():
    row = row_to_restaurant(_sample_row(), 0)
    assert row is not None
    assert row.location == "Bangalore"
    assert row.location_key == "bangalore"
    assert row.matches_location("bangalore")
    assert row.matches_location("BANGALORE")


def test_row_to_restaurant_valid():
    restaurant = row_to_restaurant(_sample_row(), 0)
    assert restaurant is not None
    assert restaurant.id.startswith("r_")
    assert restaurant.name == "Test Bistro"
    assert len(restaurant.cuisines) == 2
    assert restaurant.rating == 4.2
    assert restaurant.cost_for_two == 800
    assert restaurant.budget_tier == BudgetTier.MEDIUM
    assert restaurant.attributes["locality"] == "Indiranagar"


def test_skip_missing_name():
    assert row_to_restaurant(_sample_row(name=""), 0) is None


def test_skip_missing_location():
    assert row_to_restaurant(_sample_row(address=""), 0) is None


def test_null_rating_keeps_row():
    restaurant = row_to_restaurant(_sample_row(rate="-"), 0)
    assert restaurant is not None
    assert restaurant.rating is None


def test_null_cost_null_budget_tier():
    restaurant = row_to_restaurant(
        _sample_row(**{"approx_cost(for two people)": "-"}),
        0,
    )
    assert restaurant is not None
    assert restaurant.cost_for_two is None
    assert restaurant.budget_tier is None


def test_preprocess_rows_skips_invalid_without_crash():
    rows = [
        _sample_row(),
        _sample_row(name=""),
        _sample_row(address=""),
    ]
    result = preprocess_rows(rows)
    assert result.stats.accepted == 1
    assert result.stats.skipped_missing_name == 1
    assert result.stats.skipped_missing_location == 1


def test_stable_id_from_url():
    r1 = row_to_restaurant(_sample_row(), 0)
    r2 = row_to_restaurant(_sample_row(), 99)
    assert r1 is not None and r2 is not None
    assert r1.id == r2.id
