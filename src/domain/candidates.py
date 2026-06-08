"""Build compact candidate payloads for LLM prompts (Phase 2)."""

from __future__ import annotations

from typing import Any

from src.models.restaurant import Restaurant

CANDIDATE_FIELDS = (
    "id",
    "name",
    "cuisines",
    "rating",
    "cost_for_two",
    "budget_tier",
    "location",
)


def to_candidate(restaurant: Restaurant) -> dict[str, Any]:
    """Single JSON-serializable candidate dict (F-11)."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "cuisines": list(restaurant.cuisines),
        "rating": restaurant.rating,
        "cost_for_two": restaurant.cost_for_two,
        "budget_tier": (
            restaurant.budget_tier.value if restaurant.budget_tier is not None else None
        ),
        "location": restaurant.location,
    }


def to_candidates(restaurants: list[Restaurant]) -> list[dict[str, Any]]:
    """Map filtered restaurants to minimal prompt payloads."""
    return [to_candidate(r) for r in restaurants]
