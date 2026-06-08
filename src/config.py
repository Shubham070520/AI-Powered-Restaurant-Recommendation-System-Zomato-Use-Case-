"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class Settings(BaseSettings):
    """Project settings with defaults from architecture docs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    hf_dataset_name: str = Field(
        default="ManikaSaini/zomato-restaurant-recommendation",
        validation_alias="HF_DATASET_NAME",
    )
    data_cache_path: Optional[Path] = Field(
        default=None,
        validation_alias="DATA_CACHE_PATH",
    )
    llm_provider: str = Field(default="groq", validation_alias="LLM_PROVIDER")
    llm_api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY")
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias="LLM_MODEL",
    )
    llm_base_url: Optional[str] = Field(default=None, validation_alias="LLM_BASE_URL")
    llm_timeout_seconds: float = Field(default=30.0, validation_alias="LLM_TIMEOUT_SECONDS")
    max_candidates_for_llm: int = Field(
        default=25,
        validation_alias="MAX_CANDIDATES_FOR_LLM",
    )

    @field_validator("max_candidates_for_llm", mode="before")
    @classmethod
    def _coerce_max_candidates(cls, value: object) -> int:
        if value is None or value == "":
            return 25
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "MAX_CANDIDATES_FOR_LLM must be a positive integer."
            ) from exc
        if parsed <= 0:
            raise ValueError(
                "MAX_CANDIDATES_FOR_LLM must be a positive integer."
            )
        return parsed

    @field_validator("data_cache_path", mode="before")
    @classmethod
    def _empty_path_to_none(cls, value: object) -> Optional[Path]:
        if value is None or value == "":
            return None
        return Path(value)

    def resolved_llm_base_url(self) -> str:
        """OpenAI-compatible API base URL (Groq by default)."""
        if self.llm_base_url and str(self.llm_base_url).strip():
            return str(self.llm_base_url).rstrip("/")
        return GROQ_BASE_URL

    def require_llm_api_key(self) -> str:
        """Return Groq/API key or raise with a clear message (Phase 3+)."""
        if not self.llm_api_key or not self.llm_api_key.strip():
            raise RuntimeError(
                "LLM_API_KEY is not set. Copy .env.example to .env and add your "
                "Groq API key from https://console.groq.com/"
            )
        return self.llm_api_key.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
