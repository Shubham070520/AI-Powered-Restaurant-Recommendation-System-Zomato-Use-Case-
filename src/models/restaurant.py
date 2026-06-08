"""Canonical restaurant model (Phase 1)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class BudgetTier(str, Enum):
    """Budget band derived from cost for two (INR)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Restaurant(BaseModel):
    """Normalized restaurant record from the Zomato HF dataset."""

    id: str
    name: str
    location: str
    cuisines: list[str] = Field(default_factory=list)
    rating: Optional[float] = None
    cost_for_two: Optional[int] = None
    budget_tier: Optional[BudgetTier] = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @property
    def location_key(self) -> str:
        """Case-insensitive key for location matching (D-13)."""
        return self.location.strip().lower()

    def matches_location(self, user_location: str) -> bool:
        """Case-insensitive equality or substring match on city."""
        needle = user_location.strip().lower()
        if not needle:
            return False
        haystack = self.location_key
        return haystack == needle or needle in haystack or haystack in needle
