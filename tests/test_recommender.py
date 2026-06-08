"""Integration tests for recommendation orchestrator (Phase 4)."""

from __future__ import annotations

import json

import pytest

from src.data.store import RestaurantStore
from src.llm.client import MockLLMClient
from src.models.preferences import UserPreferences
from src.models.restaurant import BudgetTier, Restaurant
from src.services.recommender import RecommendationError, get_recommendations

FIXTURE_RESTAURANTS = [
    Restaurant(
        id="r_1",
        name="Alpha Italian",
        location="Bangalore",
        cuisines=["Italian"],
        rating=4.5,
        cost_for_two=1200,
        budget_tier=BudgetTier.MEDIUM,
    ),
    Restaurant(
        id="r_2",
        name="Beta Chinese",
        location="Bangalore",
        cuisines=["Chinese"],
        rating=4.0,
        cost_for_two=400,
        budget_tier=BudgetTier.LOW,
    ),
    Restaurant(
        id="r_3",
        name="Gamma Italian",
        location="Bangalore",
        cuisines=["Italian"],
        rating=4.2,
        cost_for_two=900,
        budget_tier=BudgetTier.MEDIUM,
    ),
]


def _store() -> RestaurantStore:
    store = RestaurantStore()
    store._set_restaurants(FIXTURE_RESTAURANTS)  # noqa: SLF001
    store._loaded = True  # noqa: SLF001
    return store


def _mock_client() -> MockLLMClient:
    payload = {
        "summary": "Two Italian spots in Bangalore.",
        "recommendations": [
            {
                "restaurant_id": "r_1",
                "rank": 1,
                "explanation": "Top Italian rating.",
            },
            {
                "restaurant_id": "r_3",
                "rank": 2,
                "explanation": "Also Italian and medium budget.",
            },
            {
                "restaurant_id": "r_hallucinated",
                "rank": 3,
                "explanation": "Should be dropped.",
            },
        ],
    }
    return MockLLMClient(json.dumps(payload))


def test_empty_filter_skips_llm():
    prefs = UserPreferences(location="NowhereCity", budget="medium")
    client = _mock_client()

    response = get_recommendations(prefs, store=_store(), client=client)

    assert response.recommendations == []
    assert response.message is not None
    assert response.meta.candidates_considered == 0


def test_merge_uses_store_fields_not_llm():
    prefs = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        top_k=2,
    )
    response = get_recommendations(prefs, store=_store(), client=_mock_client())

    assert len(response.recommendations) == 2
    top = response.recommendations[0]
    assert top.name == "Alpha Italian"
    assert top.rating == 4.5
    assert top.estimated_cost_for_two == 1200
    assert top.restaurant_id == "r_1"
    assert "Italian" in top.explanation or top.explanation


def test_meta_candidates_considered():
    prefs = UserPreferences(location="Bangalore", budget="medium", cuisine="Italian")
    response = get_recommendations(prefs, store=_store(), client=_mock_client())
    assert response.meta.candidates_considered == 2
    assert response.meta.total_matched == 2
    assert response.meta.model


def test_preferences_serialized_in_response():
    prefs = UserPreferences(location="Bangalore", budget="medium", cuisine="Italian")
    response = get_recommendations(prefs, store=_store(), client=_mock_client())
    assert response.preferences_used["location"] == "Bangalore"
    assert response.preferences_used["budget"] == "medium"


def test_all_llm_ids_invalid_raises():
    bad_client = MockLLMClient(
        json.dumps(
            {
                "summary": "x",
                "recommendations": [
                    {"restaurant_id": "r_fake", "rank": 1, "explanation": "nope"}
                ],
            }
        )
    )
    prefs = UserPreferences(location="Bangalore", budget="medium", cuisine="Italian")
    with pytest.raises(RecommendationError):
        get_recommendations(prefs, store=_store(), client=bad_client)
