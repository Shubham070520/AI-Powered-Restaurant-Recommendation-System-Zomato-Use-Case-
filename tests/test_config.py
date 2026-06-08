"""Phase 0 configuration tests."""

import pytest

from src.config import GROQ_BASE_URL, Settings, get_settings


def test_default_hf_dataset_name() -> None:
    settings = Settings()
    assert settings.hf_dataset_name == "ManikaSaini/zomato-restaurant-recommendation"


def test_default_max_candidates() -> None:
    settings = Settings()
    assert settings.max_candidates_for_llm == 25


def test_default_groq_settings() -> None:
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "groq"
    assert settings.llm_model == "llama-3.3-70b-versatile"
    assert settings.resolved_llm_base_url() == GROQ_BASE_URL


def test_require_llm_api_key_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        settings.require_llm_api_key()
    get_settings.cache_clear()


def test_require_llm_api_key_returns_stripped_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "  test-key  ")
    get_settings.cache_clear()
    settings = Settings()
    assert settings.require_llm_api_key() == "test-key"
    get_settings.cache_clear()


def test_invalid_max_candidates_raises() -> None:
    with pytest.raises(ValueError, match="MAX_CANDIDATES_FOR_LLM"):
        Settings(_env_file=None, MAX_CANDIDATES_FOR_LLM=0)

    with pytest.raises(ValueError, match="MAX_CANDIDATES_FOR_LLM"):
        Settings(_env_file=None, MAX_CANDIDATES_FOR_LLM="not-a-number")
