"""Phase 3 integration demo: rank 5 toy candidates via Groq or mock."""

from __future__ import annotations

import argparse
import json
import logging
import os

from src.llm.client import MockLLMClient, get_llm_client
from src.llm.parser import rank_candidates
from src.models.preferences import UserPreferences

TOY_CANDIDATES = [
    {
        "id": "r_toy_1",
        "name": "Trattoria Roma",
        "cuisines": ["Italian", "Pizza"],
        "rating": 4.6,
        "cost_for_two": 1200,
        "budget_tier": "medium",
        "location": "Bangalore",
    },
    {
        "id": "r_toy_2",
        "name": "Dragon Wok",
        "cuisines": ["Chinese", "Thai"],
        "rating": 4.2,
        "cost_for_two": 800,
        "budget_tier": "medium",
        "location": "Bangalore",
    },
    {
        "id": "r_toy_3",
        "name": "Bella Italia",
        "cuisines": ["Italian", "Continental"],
        "rating": 4.4,
        "cost_for_two": 1400,
        "budget_tier": "medium",
        "location": "Bangalore",
    },
    {
        "id": "r_toy_4",
        "name": "Spice Garden",
        "cuisines": ["North Indian"],
        "rating": 4.0,
        "cost_for_two": 500,
        "budget_tier": "low",
        "location": "Bangalore",
    },
    {
        "id": "r_toy_5",
        "name": "Pasta Street",
        "cuisines": ["Italian", "Fast Food"],
        "rating": 4.1,
        "cost_for_two": 900,
        "budget_tier": "medium",
        "location": "Bangalore",
    },
]

MOCK_RESPONSE = json.dumps(
    {
        "summary": "Three Italian-forward picks in Bangalore within a medium budget and above 4.0 rating.",
        "recommendations": [
            {
                "restaurant_id": "r_toy_1",
                "rank": 1,
                "explanation": "Highest rating Italian option; cost fits medium budget.",
            },
            {
                "restaurant_id": "r_toy_3",
                "rank": 2,
                "explanation": "Strong Italian and Continental menu; matches cuisine preference.",
            },
            {
                "restaurant_id": "r_toy_5",
                "rank": 3,
                "explanation": "Italian fast casual; good value within medium budget.",
            },
        ],
    }
)


def run_demo(*, use_mock: bool = False) -> None:
    preferences = UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        top_k=3,
    )
    client = MockLLMClient(MOCK_RESPONSE) if use_mock else get_llm_client()
    result = rank_candidates(preferences, TOY_CANDIDATES, client)

    print("Summary:", result.summary)
    print()
    for rec in result.recommendations:
        name = next(
            (c["name"] for c in TOY_CANDIDATES if c["id"] == rec.restaurant_id),
            rec.restaurant_id,
        )
        print(f"#{rec.rank} {name} ({rec.restaurant_id})")
        print(f"   {rec.explanation}")
        print()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Phase 3 LLM ranking demo")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM (no API key required)",
    )
    args = parser.parse_args()
    use_mock = args.mock or os.environ.get("USE_MOCK_LLM", "").lower() in ("1", "true", "yes")
    run_demo(use_mock=use_mock)


if __name__ == "__main__":
    main()
