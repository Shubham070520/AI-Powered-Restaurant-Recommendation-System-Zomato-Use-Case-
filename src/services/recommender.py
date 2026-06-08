"""Recommendation orchestrator (Phase 4)."""

from __future__ import annotations

import logging
import time
from typing import Optional

from pydantic import ValidationError

from src.config import get_settings
from src.data.store import RestaurantStore, get_store
from src.domain.candidates import to_candidates
from src.domain.filters import apply_filters
from src.llm.client import LLMClient, LLMClientError, get_llm_client
from src.llm.parser import ParseError, rank_candidates
from src.models.preferences import UserPreferences
from src.models.recommendation import (
    LLMRecommendationEntry,
    RecommendationItem,
    RecommendationMeta,
    RecommendationResponse,
)

logger = logging.getLogger(__name__)


class RecommendationError(RuntimeError):
    """User-safe orchestration failure."""


def _merge_item(
    entry: LLMRecommendationEntry,
    store: RestaurantStore,
) -> Optional[RecommendationItem]:
    """Enrich LLM row from store; never use LLM for name/rating/cost."""
    restaurant = store.get_by_id(entry.restaurant_id)
    if restaurant is None:
        logger.warning("LLM id not in store after merge: %s", entry.restaurant_id)
        return None
    return RecommendationItem(
        rank=entry.rank,
        restaurant_id=restaurant.id,
        name=restaurant.name,
        cuisines=list(restaurant.cuisines),
        rating=restaurant.rating,
        estimated_cost_for_two=restaurant.cost_for_two,
        budget_tier=(
            restaurant.budget_tier.value if restaurant.budget_tier is not None else None
        ),
        location=restaurant.location,
        explanation=entry.explanation,
    )


def _empty_response(
    preferences: UserPreferences,
    *,
    message: str,
    total_matched: int = 0,
    truncated: bool = False,
) -> RecommendationResponse:
    settings = get_settings()
    return RecommendationResponse(
        summary="",
        preferences_used=preferences.model_dump(mode="json"),
        recommendations=[],
        message=message,
        meta=RecommendationMeta(
            candidates_considered=0,
            total_matched=total_matched,
            truncated=truncated,
            model=settings.llm_model,
            provider=settings.llm_provider,
        ),
    )


def get_recommendations(
    preferences: UserPreferences,
    *,
    store: Optional[RestaurantStore] = None,
    client: Optional[LLMClient] = None,
) -> RecommendationResponse:
    """
    End-to-end: validate → filter → LLM rank → merge with store.

  Empty filter results skip the LLM (F-01).
    """
    restaurant_store = store or get_store()
    settings = get_settings()

    filter_result = apply_filters(preferences, restaurant_store.get_all())
    logger.info(
        "Filter matched %s restaurants (truncated=%s)",
        filter_result.total_matched,
        filter_result.truncated,
    )

    if filter_result.is_empty:
        return _empty_response(
            preferences,
            message=filter_result.message or "No restaurants match your preferences.",
            total_matched=filter_result.total_matched,
        )

    candidates = to_candidates(filter_result.candidates)
    llm_client = client or get_llm_client()

    started = time.perf_counter()
    try:
        llm_result = rank_candidates(preferences, candidates, llm_client)
    except ParseError as exc:
        logger.exception("Failed to parse LLM response")
        raise RecommendationError(
            "Could not understand the AI response. Please try again."
        ) from exc
    except LLMClientError:
        raise
    except Exception as exc:
        logger.exception("Unexpected LLM failure")
        raise RecommendationError(
            "Recommendation service failed. Please try again later."
        ) from exc
    latency_ms = (time.perf_counter() - started) * 1000
    logger.info("LLM call completed in %.0f ms", latency_ms)

    merged: list[RecommendationItem] = []
    for entry in llm_result.recommendations:
        item = _merge_item(entry, restaurant_store)
        if item is not None:
            merged.append(item)

    merged.sort(key=lambda i: (i.rank, i.name.lower()))

    if not merged:
        raise RecommendationError(
            "No valid recommendations could be built from the AI response."
        )

    return RecommendationResponse(
        summary=llm_result.summary,
        preferences_used=preferences.model_dump(mode="json"),
        recommendations=merged,
        meta=RecommendationMeta(
            candidates_considered=len(candidates),
            total_matched=filter_result.total_matched,
            truncated=filter_result.truncated,
            model=settings.llm_model,
            provider=settings.llm_provider,
            llm_latency_ms=round(latency_ms, 1),
        ),
    )


def get_recommendations_from_dict(data: dict) -> RecommendationResponse:
    """Parse preferences dict and run orchestrator (raises ValidationError)."""
    preferences = UserPreferences.model_validate(data)
    return get_recommendations(preferences)
