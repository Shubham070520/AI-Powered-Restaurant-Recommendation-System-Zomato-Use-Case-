"""Parse and validate LLM JSON responses (Phase 3)."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

from src.llm.client import LLMClient
from src.llm.prompts import build_messages
from src.models.preferences import UserPreferences
from src.models.recommendation import LLMRecommendationEntry, LLMRecommendationResult

logger = logging.getLogger(__name__)

JSON_RETRY_SUFFIX = (
    "\n\nYour previous response was not valid JSON. "
    "Respond with a single JSON object only — no markdown fences, no extra text."
)


class ParseError(ValueError):
    """LLM output could not be parsed or validated."""


def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers (L-07)."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_object(text: str) -> str:
    """Best-effort extract first JSON object from text."""
    cleaned = strip_markdown_fences(text)
    if cleaned.startswith("{"):
        return cleaned

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        return match.group(0)
    return cleaned


def _dedupe_recommendations(
    entries: list[LLMRecommendationEntry],
) -> list[LLMRecommendationEntry]:
    """Keep best (lowest) rank per restaurant_id (L-11)."""
    by_id: dict[str, LLMRecommendationEntry] = {}
    for entry in entries:
        existing = by_id.get(entry.restaurant_id)
        if existing is None or entry.rank < existing.rank:
            by_id[entry.restaurant_id] = entry
    return list(by_id.values())


def parse_llm_response(
    raw: str,
    valid_ids: set[str],
    *,
    drop_unknown_ids: bool = True,
) -> LLMRecommendationResult:
    """
    Parse raw LLM text into LLMRecommendationResult.

    Unknown restaurant_id values are dropped with a warning when drop_unknown_ids=True.
    Raises ParseError if JSON/schema invalid or no valid recommendations remain.
    """
    json_text = _extract_json_object(raw)
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ParseError("LLM response is not valid JSON") from exc

    try:
        result = LLMRecommendationResult.model_validate(payload)
    except ValidationError as exc:
        raise ParseError(f"LLM response schema invalid: {exc}") from exc

    filtered: list[LLMRecommendationEntry] = []
    for entry in result.recommendations:
        if entry.restaurant_id in valid_ids:
            filtered.append(entry)
        elif drop_unknown_ids:
            logger.warning(
                "Dropping unknown restaurant_id from LLM output: %s",
                entry.restaurant_id,
            )
        else:
            raise ParseError(f"Unknown restaurant_id: {entry.restaurant_id}")

    if not filtered and result.recommendations:
        raise ParseError("No valid restaurant_id values in LLM response")

    filtered = _dedupe_recommendations(filtered)
    filtered.sort(key=lambda e: (e.rank, e.restaurant_id))

    return LLMRecommendationResult(summary=result.summary, recommendations=filtered)


def complete_and_parse(
    client: LLMClient,
    system: str,
    user: str,
    valid_ids: set[str],
    *,
    retry_on_parse_failure: bool = True,
) -> LLMRecommendationResult:
    """Call LLM once; optional second call on parse failure (I3-1)."""
    raw = client.complete(system, user)
    try:
        return parse_llm_response(raw, valid_ids)
    except ParseError:
        if not retry_on_parse_failure:
            raise
        logger.info("Parse failed; retrying LLM with JSON-only instruction")
        raw_retry = client.complete(system, user + JSON_RETRY_SUFFIX)
        return parse_llm_response(raw_retry, valid_ids)


def rank_candidates(
    preferences: UserPreferences,
    candidates: list[dict],
    client: LLMClient,
    *,
    top_k: int | None = None,
) -> LLMRecommendationResult:
    """Build prompts, call LLM, parse and validate ids."""
    if not candidates:
        raise ParseError("Cannot rank an empty candidate list")

    k = top_k if top_k is not None else preferences.top_k
    system, user = build_messages(preferences, candidates, top_k=k)
    valid_ids = {str(c["id"]) for c in candidates}
    return complete_and_parse(client, system, user, valid_ids)
