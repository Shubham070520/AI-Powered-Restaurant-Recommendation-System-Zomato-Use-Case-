"""CLI for end-to-end recommendations (Phase 4)."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from pydantic import ValidationError

from src.llm.client import LLMClientError
from src.models.preferences import UserPreferences
from src.services.recommender import RecommendationError, get_recommendations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Get restaurant recommendations (JSON output)",
    )
    parser.add_argument(
        "--json",
        help="Preferences as JSON string or path to .json file (use - for stdin)",
    )
    parser.add_argument("--location", help="City or area")
    parser.add_argument("--budget", choices=["low", "medium", "high"])
    parser.add_argument("--cuisine", default=None)
    parser.add_argument("--min-rating", type=float, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument(
        "--additional",
        nargs="*",
        default=None,
        help="Additional preference tags",
    )
    return parser


def _load_json_arg(value: str) -> dict:
    if value == "-":
        return json.load(sys.stdin)
    if value.endswith(".json"):
        with open(value, encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(value)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.json:
            data = _load_json_arg(args.json)
            preferences = UserPreferences.model_validate(data)
        else:
            if not args.location or not args.budget:
                parser.error("Provide --json or both --location and --budget")
            preferences = UserPreferences(
                location=args.location,
                budget=args.budget,
                cuisine=args.cuisine,
                min_rating=args.min_rating,
                top_k=args.top_k or 5,
                additional_preferences=args.additional or [],
            )
        response = get_recommendations(preferences)
    except ValidationError as exc:
        print(json.dumps({"error": "validation", "detail": exc.errors()}), file=sys.stderr)
        return 2
    except (LLMClientError, RecommendationError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
