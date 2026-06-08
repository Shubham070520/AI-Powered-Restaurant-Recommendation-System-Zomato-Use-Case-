"""Map raw Hugging Face rows to canonical Restaurant records.

Dataset schema (ManikaSaini/zomato-restaurant-recommendation, train split):
  url, address, name, online_order, book_table, rate, votes, phone, location,
  rest_type, dish_liked, cuisines, approx_cost(for two people), reviews_list,
  menu_item, listed_in(type), listed_in(city)

See docs/dataset-notes.md for column mapping and policies.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Optional

from src.models.restaurant import BudgetTier, Restaurant

logger = logging.getLogger(__name__)

# Budget thresholds (INR) — architecture §4.1
BUDGET_LOW_MAX = 500
BUDGET_MEDIUM_MAX = 1500

COST_COLUMN = "approx_cost(for two people)"
BANGALORE_ALIASES = frozenset(
    {"bangalore", "bengaluru", "bengalore", "banglore", "banglore"}
)


@dataclass
class PreprocessStats:
    """Counts from a preprocessing run."""

    total_rows: int = 0
    accepted: int = 0
    skipped_missing_name: int = 0
    skipped_missing_location: int = 0
    skipped_invalid: int = 0

    @property
    def skipped(self) -> int:
        return (
            self.skipped_missing_name
            + self.skipped_missing_location
            + self.skipped_invalid
        )


@dataclass
class PreprocessResult:
    restaurants: list[Restaurant] = field(default_factory=list)
    stats: PreprocessStats = field(default_factory=PreprocessStats)


def normalize_location_display(city: str) -> str:
    """Trim and title-case city for display; compare via location_key."""
    return city.strip()


def extract_city(address: Optional[str]) -> Optional[str]:
    """Derive city from address; normalize Bangalore spellings."""
    if not address or not str(address).strip():
        return None

    text = str(address).strip()
    lower = text.lower()
    if any(alias in lower for alias in ("bangalore", "bengaluru", "bengalore", "banglore")):
        return "Bangalore"

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return None

    for part in reversed(parts):
        normalized = part.rstrip(".").strip()
        key = normalized.lower()
        if key in BANGALORE_ALIASES or "bangalore" in key or "bengaluru" in key:
            return "Bangalore"
        if len(normalized) <= 40 and key not in ("india", "karnataka"):
            return normalized.title()

    return None


def parse_rating(value: Any) -> Optional[float]:
    """Parse rate field (e.g. '4.1/5', '-', 'NEW')."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw in ("-", "NEW", "nan"):
        return None
    if "/" in raw:
        raw = raw.split("/")[0].strip()
    raw = re.sub(r"[^\d.]", "", raw)
    if not raw:
        return None
    try:
        rating = float(raw)
    except ValueError:
        return None
    if rating < 0 or rating > 5:
        return None
    return rating


def parse_cost(value: Any) -> Optional[int]:
    """Parse approx cost; handles commas and simple ranges (D-07)."""
    if value is None:
        return None
    raw = str(value).strip().replace(",", "").replace("₹", "").strip()
    if not raw or raw in ("-", "nan"):
        return None

    if "-" in raw:
        parts = re.findall(r"\d+", raw)
        if not parts:
            return None
        nums = [int(p) for p in parts]
        return int(sum(nums) / len(nums))

    digits = re.sub(r"[^\d.]", "", raw)
    if not digits:
        return None
    try:
        cost = int(float(digits))
    except ValueError:
        return None
    if cost < 0:
        return None
    return cost


def assign_budget_tier(cost: Optional[int]) -> Optional[BudgetTier]:
    if cost is None:
        return None
    if cost <= BUDGET_LOW_MAX:
        return BudgetTier.LOW
    if cost <= BUDGET_MEDIUM_MAX:
        return BudgetTier.MEDIUM
    return BudgetTier.HIGH


def split_cuisines(value: Any) -> list[str]:
    """Split multi-cuisine string; trim tokens (D-11, D-12)."""
    if value is None:
        return []
    raw = str(value).strip()
    if not raw:
        return []
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    return tokens


def make_restaurant_id(row: dict[str, Any], index: int) -> str:
    """Stable id from url or row index (D-10)."""
    url = row.get("url")
    if url and str(url).strip():
        digest = hashlib.sha256(str(url).encode("utf-8")).hexdigest()[:16]
        return f"r_{digest}"
    return f"r_{index}"


def row_to_restaurant(row: dict[str, Any], index: int) -> Optional[Restaurant]:
    name = (row.get("name") or "").strip()
    if not name:
        return None

    city = extract_city(row.get("address"))
    if not city:
        return None

    cost = parse_cost(row.get(COST_COLUMN))
    locality = (row.get("location") or "").strip()

    attributes: dict[str, Any] = {}
    if locality:
        attributes["locality"] = locality
    if row.get("rest_type"):
        attributes["rest_type"] = str(row["rest_type"]).strip()
    if row.get("online_order"):
        attributes["online_order"] = str(row["online_order"]).strip()
    if row.get("book_table"):
        attributes["book_table"] = str(row["book_table"]).strip()
    if row.get("address"):
        attributes["address"] = str(row["address"]).strip()

    return Restaurant(
        id=make_restaurant_id(row, index),
        name=name,
        location=normalize_location_display(city),
        cuisines=split_cuisines(row.get("cuisines")),
        rating=parse_rating(row.get("rate")),
        cost_for_two=cost,
        budget_tier=assign_budget_tier(cost),
        attributes=attributes,
    )


def preprocess_rows(
    rows: Iterable[dict[str, Any]],
) -> PreprocessResult:
    """Convert raw dataset rows to Restaurant list with skip logging."""
    result = PreprocessResult()
    for index, row in enumerate(rows):
        result.stats.total_rows += 1
        name = (row.get("name") or "").strip()
        if not name:
            result.stats.skipped_missing_name += 1
            continue
        if not extract_city(row.get("address")):
            result.stats.skipped_missing_location += 1
            continue
        try:
            restaurant = row_to_restaurant(row, index)
        except Exception:
            logger.exception("Failed to preprocess row index=%s", index)
            result.stats.skipped_invalid += 1
            continue
        if restaurant is None:
            result.stats.skipped_invalid += 1
            continue
        result.restaurants.append(restaurant)
        result.stats.accepted += 1

    if result.stats.skipped:
        logger.info(
            "Preprocessing complete: accepted=%s skipped=%s (name=%s location=%s invalid=%s)",
            result.stats.accepted,
            result.stats.skipped,
            result.stats.skipped_missing_name,
            result.stats.skipped_missing_location,
            result.stats.skipped_invalid,
        )
    return result


def preprocess_rows_iter(
    rows: Iterable[dict[str, Any]],
) -> Iterator[Restaurant]:
    """Yield restaurants one at a time (for large streams)."""
    for index, row in enumerate(rows):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        if not extract_city(row.get("address")):
            continue
        restaurant = row_to_restaurant(row, index)
        if restaurant is not None:
            yield restaurant
