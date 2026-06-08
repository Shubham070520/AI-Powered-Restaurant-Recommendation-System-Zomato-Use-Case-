"""Hard-filter restaurants by user preferences (Phase 2)."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from src.config import get_settings
from src.models.preferences import UserPreferences
from src.models.recommendation import FilterResult
from src.models.restaurant import BudgetTier, Restaurant

logger = logging.getLogger(__name__)

EMPTY_FILTER_MESSAGE = (
    "No restaurants match your preferences. "
    "Try a different location, budget, cuisine, or minimum rating."
)


def _sort_key_for_truncation(restaurant: Restaurant) -> tuple:
    """Higher rating first; missing rating last; stable tie-break by name (F-04)."""
    rating = restaurant.rating if restaurant.rating is not None else -1.0
    return (-rating, restaurant.name.lower(), restaurant.id)


def filter_by_location(restaurants: Iterable[Restaurant], location: str) -> list[Restaurant]:
    return [r for r in restaurants if r.matches_location(location)]


def filter_by_budget(restaurants: Iterable[Restaurant], budget: BudgetTier) -> list[Restaurant]:
    """Rows without budget_tier are excluded when user selects a budget (F-08, D-06)."""
    return [r for r in restaurants if r.budget_tier is not None and r.budget_tier == budget]


def matches_cuisine(restaurant: Restaurant, cuisine: str) -> bool:
    """Case-insensitive token or substring match (F-06, F-05)."""
    needle = cuisine.strip().lower()
    if not needle:
        return True
    for token in restaurant.cuisines:
        haystack = token.lower()
        if needle in haystack or haystack in needle:
            return True
    return False


def filter_by_cuisine(restaurants: Iterable[Restaurant], cuisine: str) -> list[Restaurant]:
    return [r for r in restaurants if matches_cuisine(r, cuisine)]


def filter_by_min_rating(
    restaurants: Iterable[Restaurant], min_rating: float
) -> list[Restaurant]:
    """Include only rows with rating >= min_rating; null ratings excluded (D-05, F-09)."""
    return [
        r
        for r in restaurants
        if r.rating is not None and r.rating >= min_rating
    ]


def truncate_candidates(
    restaurants: list[Restaurant],
    max_candidates: int,
) -> tuple[list[Restaurant], bool]:
    if len(restaurants) <= max_candidates:
        return restaurants, False
    ordered = sorted(restaurants, key=_sort_key_for_truncation)
    return ordered[:max_candidates], True


def apply_filters(
    preferences: UserPreferences,
    restaurants: Iterable[Restaurant],
    *,
    max_candidates: Optional[int] = None,
) -> FilterResult:
    """
    Run filter pipeline: location → budget → cuisine → min_rating → truncate.

    Returns empty candidates with a message when nothing matches (F-01).
    """
    limit = max_candidates if max_candidates is not None else get_settings().max_candidates_for_llm
    pool = list(restaurants)

    pool = filter_by_location(pool, preferences.location)
    pool = filter_by_budget(pool, preferences.budget_tier())
    if preferences.cuisine:
        pool = filter_by_cuisine(pool, preferences.cuisine)
    if preferences.min_rating is not None:
        pool = filter_by_min_rating(pool, preferences.min_rating)

    total_matched = len(pool)
    if total_matched == 0:
        logger.info(
            "Filter returned zero candidates for location=%r budget=%s",
            preferences.location,
            preferences.budget,
        )
        return FilterResult(
            candidates=[],
            message=EMPTY_FILTER_MESSAGE,
            total_matched=0,
            truncated=False,
        )

    candidates, truncated = truncate_candidates(pool, limit)
    if truncated:
        logger.info(
            "Truncated %s candidates to %s (max_candidates_for_llm=%s)",
            total_matched,
            len(candidates),
            limit,
        )

    return FilterResult(
        candidates=candidates,
        message=None,
        total_matched=total_matched,
        truncated=truncated,
    )


def filter_demo() -> None:
    """Phase 2 milestone: load store, filter, print candidates (no LLM)."""
    from src.data.store import get_store
    from src.domain.candidates import to_candidates
    from src.models.preferences import UserPreferences

    preferences = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
    )
    store = get_store()
    result = apply_filters(preferences, store.get_all())
    candidates = to_candidates(result.candidates)

    print(
        f"Preferences: {preferences.location}, {preferences.budget}, "
        f"cuisine={preferences.cuisine!r}, min_rating={preferences.min_rating}"
    )
    print(
        f"Matched {result.total_matched} restaurants"
        + (f" (truncated to {len(candidates)})" if result.truncated else "")
    )
    if result.message:
        print(result.message)
        return

    print(f"Sending {len(candidates)} candidates to LLM (max {get_settings().max_candidates_for_llm})")
    for item in candidates[:3]:
        print(item)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    filter_demo()
