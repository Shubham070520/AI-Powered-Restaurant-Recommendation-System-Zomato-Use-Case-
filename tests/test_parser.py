"""Unit tests for LLM prompts and parser (Phase 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.llm.client import DynamicMockLLMClient, GroqLLMClient, LLMClientError, MockLLMClient
from src.llm.parser import ParseError, complete_and_parse, parse_llm_response, rank_candidates, strip_markdown_fences
from src.llm.prompts import build_messages, prompts_contain_only_provided_constraint
from src.models.preferences import UserPreferences

FIXTURES = Path(__file__).parent / "fixtures"
VALID_IDS = {"r_1", "r_2", "r_3"}


def _prefs() -> UserPreferences:
    return UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=3,
    )


def test_strip_markdown_fences():
    raw = (FIXTURES / "llm_fenced_json.txt").read_text(encoding="utf-8")
    cleaned = strip_markdown_fences(raw)
    assert cleaned.startswith("{")
    assert "```" not in cleaned


def test_parse_valid_json_fixture():
    raw = (FIXTURES / "llm_valid_response.json").read_text(encoding="utf-8")
    result = parse_llm_response(raw, VALID_IDS)
    assert result.summary
    assert len(result.recommendations) == 2
    assert result.recommendations[0].restaurant_id == "r_1"
    assert result.recommendations[0].rank == 1


def test_parse_fenced_json_fixture():
    raw = (FIXTURES / "llm_fenced_json.txt").read_text(encoding="utf-8")
    result = parse_llm_response(raw, {"r_1"})
    assert len(result.recommendations) == 1


def test_parse_drops_unknown_ids():
    payload = {
        "summary": "Test",
        "recommendations": [
            {"restaurant_id": "r_1", "rank": 1, "explanation": "ok"},
            {"restaurant_id": "r_fake", "rank": 2, "explanation": "bad"},
        ],
    }
    result = parse_llm_response(json.dumps(payload), VALID_IDS)
    assert len(result.recommendations) == 1
    assert result.recommendations[0].restaurant_id == "r_1"


def test_parse_all_invalid_ids_raises():
    payload = {
        "summary": "Test",
        "recommendations": [
            {"restaurant_id": "r_fake", "rank": 1, "explanation": "nope"},
        ],
    }
    with pytest.raises(ParseError, match="No valid restaurant_id"):
        parse_llm_response(json.dumps(payload), VALID_IDS)


def test_parse_prose_only_fails():
    with pytest.raises(ParseError, match="not valid JSON"):
        parse_llm_response("Here are my picks: Trattoria Roma is great!", VALID_IDS)


def test_parse_missing_recommendations_key_raises():
    with pytest.raises(ParseError, match="schema invalid"):
        parse_llm_response(json.dumps({"summary": "only summary"}), VALID_IDS)


def test_parse_dedupes_duplicate_ids():
    payload = {
        "summary": "Dup",
        "recommendations": [
            {"restaurant_id": "r_1", "rank": 2, "explanation": "second"},
            {"restaurant_id": "r_1", "rank": 1, "explanation": "first"},
        ],
    }
    result = parse_llm_response(json.dumps(payload), VALID_IDS)
    assert len(result.recommendations) == 1
    assert result.recommendations[0].rank == 1


def test_parse_sorts_by_rank():
    payload = {
        "summary": "Order",
        "recommendations": [
            {"restaurant_id": "r_2", "rank": 2, "explanation": "b"},
            {"restaurant_id": "r_1", "rank": 1, "explanation": "a"},
        ],
    }
    result = parse_llm_response(json.dumps(payload), VALID_IDS)
    assert [r.restaurant_id for r in result.recommendations] == ["r_1", "r_2"]


def test_build_messages_contains_only_provided_constraint():
    candidates = [{"id": "r_1", "name": "A", "cuisines": [], "rating": 4.0, "cost_for_two": 100, "budget_tier": "low", "location": "X"}]
    system, user = build_messages(_prefs(), candidates)
    assert prompts_contain_only_provided_constraint(system, user)
    assert "Italian" in user
    assert "r_1" in user


def test_complete_and_parse_with_mock():
    raw = (FIXTURES / "llm_valid_response.json").read_text(encoding="utf-8")
    client = MockLLMClient(raw)
    system, user = build_messages(_prefs(), [{"id": "r_1", "name": "A", "cuisines": [], "rating": 4, "cost_for_two": 1, "budget_tier": "low", "location": "X"}])
    result = complete_and_parse(client, system, user, {"r_1", "r_2"})
    assert len(result.recommendations) >= 1


def test_complete_and_parse_retries_on_bad_json():
    calls: list[int] = []

    class FlakyClient(MockLLMClient):
        def complete(self, system: str, user: str) -> str:
            calls.append(1)
            if len(calls) == 1:
                return "not json at all"
            return (FIXTURES / "llm_valid_response.json").read_text(encoding="utf-8")

    client = FlakyClient("")
    system, user = build_messages(_prefs(), [{"id": "r_1", "name": "A", "cuisines": [], "rating": 4, "cost_for_two": 1, "budget_tier": "low", "location": "X"}])
    result = complete_and_parse(client, system, user, {"r_1", "r_2"})
    assert len(calls) == 2
    assert result.recommendations


def test_rank_candidates_integration_mock():
    candidates = [
        {"id": "r_toy_1", "name": "A", "cuisines": ["Italian"], "rating": 4.5, "cost_for_two": 1000, "budget_tier": "medium", "location": "Bangalore"},
    ]
    client = MockLLMClient(
        json.dumps(
            {
                "summary": "One pick.",
                "recommendations": [
                    {"restaurant_id": "r_toy_1", "rank": 1, "explanation": "Italian match."}
                ],
            }
        )
    )
    result = rank_candidates(_prefs(), candidates, client)
    assert result.recommendations[0].restaurant_id == "r_toy_1"


def test_dynamic_mock_llm_client():
    candidates = [
        {"id": "r_toy_1", "name": "A", "cuisines": ["Italian"], "rating": 4.5, "cost_for_two": 1000, "budget_tier": "medium", "location": "Bangalore"},
        {"id": "r_toy_2", "name": "B", "cuisines": ["Chinese"], "rating": 4.0, "cost_for_two": 800, "budget_tier": "medium", "location": "Bangalore"},
    ]
    client = DynamicMockLLMClient()
    result = rank_candidates(_prefs(), candidates, client)
    assert len(result.recommendations) == 2
    assert result.recommendations[0].restaurant_id == "r_toy_1"
    assert result.recommendations[1].restaurant_id == "r_toy_2"
    assert "medium" in result.recommendations[0].explanation


def test_require_llm_api_key_for_groq_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    from src.config import get_settings, Settings

    get_settings.cache_clear()
    monkeypatch.setattr("src.llm.client.get_settings", lambda: Settings(_env_file=None))
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        GroqLLMClient()
    get_settings.cache_clear()


def test_groq_client_401_message(monkeypatch: pytest.MonkeyPatch):
    """401 must not echo the API key (L-02)."""
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("LLM_API_KEY", "secret-key-12345")
    from src.config import get_settings

    get_settings.cache_clear()

    client = GroqLLMClient()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.request = MagicMock()

    from openai import APIStatusError

    api_error = APIStatusError("Unauthorized", response=mock_response, body=None)

    with patch.object(
        client._client.chat.completions,
        "create",
        side_effect=api_error,
    ):
        with pytest.raises(LLMClientError) as exc_info:
            client.complete("sys", "user")

    assert "secret-key" not in str(exc_info.value)
    assert "API key" in str(exc_info.value)
    get_settings.cache_clear()
