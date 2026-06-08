"""Unit tests for preferences validation and filtering (Phase 2)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.domain.candidates import CANDIDATE_FIELDS, to_candidate, to_candidates
from src.domain.filters import (
    apply_filters,
    filter_by_budget,
    filter_by_cuisine,
    filter_by_location,
    filter_by_min_rating,
    matches_cuisine,
    truncate_candidates,
)
from src.models.preferences import UserPreferences
from src.models.restaurant import BudgetTier, Restaurant

FIXTURE_RESTAURANTS = [
    Restaurant(
        id="r1",
        name="Alpha Bistro",
        location="Bangalore",
        cuisines=["Italian", "Continental"],
        rating=4.5,
        cost_for_two=1200,
        budget_tier=BudgetTier.MEDIUM,
    ),
    Restaurant(
        id="r2",
        name="Beta Wok",
        location="Bangalore",
        cuisines=["Chinese"],
        rating=4.0,
        cost_for_two=400,
        budget_tier=BudgetTier.LOW,
    ),
    Restaurant(
        id="r3",
        name="Gamma Palace",
        location="Bangalore",
        cuisines=["Italian"],
        rating=3.8,
        cost_for_two=2000,
        budget_tier=BudgetTier.HIGH,
    ),
    Restaurant(
        id="r4",
        name="Delta Delhi",
        location="Delhi",
        cuisines=["Italian"],
        rating=4.2,
        cost_for_two=800,
        budget_tier=BudgetTier.MEDIUM,
    ),
    Restaurant(
        id="r5",
        name="Epsilon Dosa",
        location="Bangalore",
        cuisines=["South Indian"],
        rating=4.0,
        cost_for_two=600,
        budget_tier=BudgetTier.MEDIUM,
    ),
    Restaurant(
        id="r6",
        name="Zeta Unknown Rating",
        location="Bangalore",
        cuisines=["Italian"],
        rating=None,
        cost_for_two=900,
        budget_tier=BudgetTier.MEDIUM,
    ),
    Restaurant(
        id="r7",
        name="Eta No Budget",
        location="Bangalore",
        cuisines=["Italian"],
        rating=4.5,
        cost_for_two=None,
        budget_tier=None,
    ),
]


def test_empty_location_rejected():
    with pytest.raises(ValidationError):
        UserPreferences(location="", budget="medium")


def test_whitespace_location_rejected():
    with pytest.raises(ValidationError):
        UserPreferences(location="   ", budget="medium")


def test_invalid_budget_rejected():
    with pytest.raises(ValidationError):
        UserPreferences(location="Bangalore", budget="cheap")  # type: ignore[arg-type]


def test_min_rating_out_of_range_rejected():
    with pytest.raises(ValidationError):
        UserPreferences(location="Bangalore", budget="medium", min_rating=6.0)


def test_top_k_zero_rejected():
    with pytest.raises(ValidationError):
        UserPreferences(location="Bangalore", budget="medium", top_k=0)


def test_top_k_capped_at_10():
    prefs = UserPreferences(location="Bangalore", budget="medium", top_k=50)
    assert prefs.top_k == 10


def test_top_k_default_is_5():
    prefs = UserPreferences(location="Bangalore", budget="medium")
    assert prefs.top_k == 5


def test_filter_location_case_insensitive():
    bangalore = filter_by_location(FIXTURE_RESTAURANTS, "bangalore")
    assert {r.id for r in bangalore} == {"r1", "r2", "r3", "r5", "r6", "r7"}


def test_filter_budget_excludes_null_tier():
    medium = filter_by_budget(FIXTURE_RESTAURANTS, BudgetTier.MEDIUM)
    assert "r7" not in {r.id for r in medium}


def test_matches_cuisine_case_insensitive():
    assert matches_cuisine(FIXTURE_RESTAURANTS[0], "italian")
    assert matches_cuisine(FIXTURE_RESTAURANTS[4], "indian")  # South Indian


def test_filter_min_rating_boundary():
    rated = filter_by_min_rating(FIXTURE_RESTAURANTS, 4.0)
    ids = {r.id for r in rated}
    assert "r2" in ids  # exactly 4.0
    assert "r3" not in ids  # 3.8
    assert "r6" not in ids  # null rating


def test_apply_filters_full_matrix():
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
    )
    result = apply_filters(prefs, FIXTURE_RESTAURANTS, max_candidates=25)
    assert result.candidates == [FIXTURE_RESTAURANTS[0]]
    assert result.message is None
    assert result.total_matched == 1


def test_apply_filters_empty_unknown_city():
    prefs = UserPreferences(location="ZZZ_NoCity", budget="medium")
    result = apply_filters(prefs, FIXTURE_RESTAURANTS)
    assert result.candidates == []
    assert result.message is not None
    assert result.is_empty


def test_apply_filters_no_cuisine_returns_more():
    with_cuisine = apply_filters(
        UserPreferences(location="Bangalore", budget="medium", cuisine="Italian"),
        FIXTURE_RESTAURANTS,
        max_candidates=25,
    )
    without_cuisine = apply_filters(
        UserPreferences(location="Bangalore", budget="medium"),
        FIXTURE_RESTAURANTS,
        max_candidates=25,
    )
    assert len(without_cuisine.candidates) > len(with_cuisine.candidates)


def test_truncation_respects_max():
    prefs = UserPreferences(location="Bangalore", budget="medium")
    result = apply_filters(prefs, FIXTURE_RESTAURANTS, max_candidates=2)
    assert len(result.candidates) == 2
    assert result.truncated is True
    assert result.total_matched > 2


def test_truncation_keeps_higher_ratings():
    prefs = UserPreferences(location="Bangalore", budget="medium")
    result = apply_filters(prefs, FIXTURE_RESTAURANTS, max_candidates=2)
    ratings = [r.rating for r in result.candidates]
    assert ratings == sorted(ratings, reverse=True)


def test_truncation_stable_tiebreak_by_name():
    tied = [
        Restaurant(
            id="a",
            name="Zulu",
            location="Bangalore",
            cuisines=[],
            rating=4.0,
            budget_tier=BudgetTier.MEDIUM,
        ),
        Restaurant(
            id="b",
            name="Alpha",
            location="Bangalore",
            cuisines=[],
            rating=4.0,
            budget_tier=BudgetTier.MEDIUM,
        ),
    ]
    truncated, _ = truncate_candidates(tied, 1)
    assert truncated[0].name == "Alpha"


def test_candidate_shape_and_json_serializable():
    candidate = to_candidate(FIXTURE_RESTAURANTS[0])
    assert set(candidate.keys()) == set(CANDIDATE_FIELDS)
    json.dumps(candidate)
    assert candidate["budget_tier"] == "medium"


def test_to_candidates_list():
    payloads = to_candidates(FIXTURE_RESTAURANTS[:2])
    assert len(payloads) == 2
    assert all(set(p.keys()) == set(CANDIDATE_FIELDS) for p in payloads)


def test_filter_by_cuisine_only():
    italian = filter_by_cuisine(FIXTURE_RESTAURANTS, "Italian")
    assert {r.id for r in italian} == {"r1", "r3", "r4", "r6", "r7"}
