"""Prompt construction for restaurant ranking (Phase 3)."""

from __future__ import annotations

import json
from typing import Any

from src.models.preferences import UserPreferences

SYSTEM_PROMPT = """You are a restaurant recommendation assistant.

Rules:
- Use ONLY the restaurants listed in the user message. Do not invent or rename restaurants.
- Every restaurant_id in your response must appear in the candidate list.
- Rank from 1 (best match) upward.
- Output valid JSON only — no markdown, no prose outside the JSON object.
"""

RESPONSE_SCHEMA_EXAMPLE = {
    "summary": "Brief overview of the top picks for the user's preferences.",
    "recommendations": [
        {
            "restaurant_id": "r_example_id",
            "rank": 1,
            "explanation": "Why this restaurant fits the user's location, budget, cuisine, and rating.",
        }
    ],
}


def build_messages(
    preferences: UserPreferences,
    candidates: list[dict[str, Any]],
    top_k: int | None = None,
) -> tuple[str, str]:
    """
    Build (system, user) messages for the LLM.

    Candidates must include `id` (from Phase 2 candidate builder).
    """
    k = top_k if top_k is not None else preferences.top_k
    prefs_payload = preferences.model_dump(mode="json")
    prefs_json = json.dumps(prefs_payload, indent=2)
    candidates_json = json.dumps(candidates, indent=2)
    schema_json = json.dumps(RESPONSE_SCHEMA_EXAMPLE, indent=2)

    user = f"""User preferences (JSON):
{prefs_json}

Candidate restaurants (JSON array; use only these — do not add any restaurant not in this list):
{candidates_json}

Task:
1. Select the top {k} restaurants that best match the user preferences.
2. Rank them 1..{k} by overall fit (location, budget, cuisine, minimum rating, and any additional preferences).
3. Write a short explanation for each pick referencing specific preference fields.
4. Include a one-paragraph summary of the overall recommendations.

Respond with JSON matching this schema exactly:
{schema_json}
"""
    return SYSTEM_PROMPT, user


def prompts_contain_only_provided_constraint(system: str, user: str) -> bool:
    """Helper for tests (L-15)."""
    combined = (system + user).lower()
    return "only" in combined and "restaurant" in combined and "do not invent" in combined
