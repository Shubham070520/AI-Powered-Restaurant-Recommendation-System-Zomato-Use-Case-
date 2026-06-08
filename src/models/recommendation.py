"""Recommendation response models (Phase 2–4)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from src.models.restaurant import Restaurant


class LLMRecommendationEntry(BaseModel):
    """Single ranked pick from the LLM (ids validated against candidates)."""

    restaurant_id: str
    rank: int = Field(ge=1)
    explanation: str

    @field_validator("restaurant_id", "explanation", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> str:
        return str(value).strip()


class LLMRecommendationResult(BaseModel):
    """Structured LLM output before merge with Restaurant store."""

    summary: str = ""
    recommendations: list[LLMRecommendationEntry]

    @field_validator("summary", mode="before")
    @classmethod
    def _strip_summary(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


class FilterResult(BaseModel):
    """Outcome of structured filtering before LLM invocation."""

    candidates: list[Restaurant] = Field(default_factory=list)
    message: Optional[str] = None
    total_matched: int = 0
    truncated: bool = False

    @property
    def is_empty(self) -> bool:
        return len(self.candidates) == 0


class RecommendationItem(BaseModel):
    """Single ranked recommendation for display (merged from store + LLM)."""

    rank: int = Field(ge=1)
    restaurant_id: str
    name: str
    cuisines: list[str] = Field(default_factory=list)
    rating: Optional[float] = None
    estimated_cost_for_two: Optional[int] = None
    budget_tier: Optional[str] = None
    location: str
    explanation: str


class RecommendationMeta(BaseModel):
    """Request metadata for UI and debugging."""

    candidates_considered: int = 0
    total_matched: int = 0
    truncated: bool = False
    model: str = ""
    provider: str = "groq"
    llm_latency_ms: Optional[float] = None


class RecommendationResponse(BaseModel):
    """Full API/UI response after orchestration."""

    summary: str = ""
    preferences_used: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    meta: RecommendationMeta = Field(default_factory=RecommendationMeta)
    message: Optional[str] = None
