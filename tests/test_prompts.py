"""Prompt builder tests (Phase 3)."""

from __future__ import annotations

from src.llm.prompts import build_messages, prompts_contain_only_provided_constraint
from src.models.preferences import UserPreferences


def test_build_messages_top_k_in_user_prompt():
    prefs = UserPreferences(location="Bangalore", budget="medium", top_k=7)
    candidates = [
        {
            "id": "r_1",
            "name": "Test",
            "cuisines": ["Italian"],
            "rating": 4.0,
            "cost_for_two": 500,
            "budget_tier": "medium",
            "location": "Bangalore",
        }
    ]
    system, user = build_messages(prefs, candidates)
    assert "top 7" in user.lower()
    assert prompts_contain_only_provided_constraint(system, user)
