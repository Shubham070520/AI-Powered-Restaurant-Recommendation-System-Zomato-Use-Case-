"""User preference model with validation (Phase 2)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from src.models.restaurant import BudgetTier

BudgetPreference = Literal["low", "medium", "high"]

TOP_K_DEFAULT = 5
TOP_K_MAX = 10


class UserPreferences(BaseModel):
    """Validated user input for filtering and LLM ranking."""

    location: str = Field(..., description="City or area (required)")
    budget: BudgetPreference
    cuisine: Optional[str] = None
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    additional_preferences: list[str] = Field(default_factory=list)
    top_k: int = Field(default=TOP_K_DEFAULT, ge=1, le=TOP_K_MAX)

    @field_validator("location", mode="before")
    @classmethod
    def _strip_location(cls, value: object) -> str:
        if value is None:
            raise ValueError("location is required")
        text = str(value).strip()
        if not text:
            raise ValueError("location must not be empty")
        return text

    @field_validator("cuisine", mode="before")
    @classmethod
    def _normalize_cuisine(cls, value: object) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("additional_preferences", mode="before")
    @classmethod
    def _coerce_additional(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [p.strip() for p in value.split(",") if p.strip()]
        return [str(p).strip() for p in value if str(p).strip()]

    @field_validator("top_k", mode="before")
    @classmethod
    def _coerce_top_k(cls, value: object) -> int:
        if value is None or value == "":
            return TOP_K_DEFAULT
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("top_k must be an integer between 1 and 10") from exc
        if parsed < 1:
            raise ValueError("top_k must be at least 1")
        if parsed > TOP_K_MAX:
            return TOP_K_MAX
        return parsed

    def budget_tier(self) -> BudgetTier:
        return BudgetTier(self.budget)
