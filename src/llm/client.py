"""LLM client abstraction and Groq implementation (Phase 3)."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from src.config import get_settings

logger = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class LLMClientError(RuntimeError):
    """User-safe LLM failure (no API key in message)."""


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return raw assistant text from the model."""


class GroqLLMClient(LLMClient):
    """Groq chat completions via OpenAI-compatible API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 1,
    ) -> None:
        settings = get_settings()
        self._model = model or settings.llm_model
        self._max_retries = max_retries
        self._client = OpenAI(
            api_key=api_key or settings.require_llm_api_key(),
            base_url=base_url or settings.resolved_llm_base_url(),
            timeout=timeout if timeout is not None else settings.llm_timeout_seconds,
        )

    def complete(self, system: str, user: str) -> str:
        last_error: Optional[Exception] = None
        attempts = self._max_retries + 1

        for attempt in range(attempts):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.2,
                )
                content = response.choices[0].message.content
                if not content:
                    raise LLMClientError("The LLM returned an empty response.")
                return content.strip()
            except APITimeoutError as exc:
                last_error = exc
                logger.warning("Groq request timed out (attempt %s/%s)", attempt + 1, attempts)
            except RateLimitError as exc:
                last_error = exc
                logger.warning("Groq rate limit (attempt %s/%s)", attempt + 1, attempts)
            except APIConnectionError as exc:
                last_error = exc
                logger.warning("Groq connection error (attempt %s/%s)", attempt + 1, attempts)
            except APIStatusError as exc:
                last_error = exc
                if exc.status_code == 401:
                    raise LLMClientError(
                        "Invalid LLM API key. Check LLM_API_KEY in your .env file."
                    ) from exc
                if exc.status_code in TRANSIENT_STATUS_CODES:
                    logger.warning(
                        "Groq HTTP %s (attempt %s/%s)",
                        exc.status_code,
                        attempt + 1,
                        attempts,
                    )
                else:
                    raise LLMClientError(
                        f"LLM request failed with status {exc.status_code}. Please try again."
                    ) from exc
            except Exception as exc:
                raise LLMClientError(f"LLM request failed: {exc}") from exc

            if attempt < attempts - 1:
                time.sleep(1.0)

        raise LLMClientError(
            "LLM request failed after retries. Please try again later."
        ) from last_error


class MockLLMClient(LLMClient):
    """Fixed response for tests and offline demos."""

    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, system: str, user: str) -> str:
        return self._response


class DynamicMockLLMClient(LLMClient):
    """Generates mock rankings dynamically based on candidates in the prompt."""

    def complete(self, system: str, user: str) -> str:
        import re
        import json

        candidates = []
        try:
            # Search for JSON array of candidate restaurants in the prompt
            match = re.search(r"Candidate restaurants \([^)]+\):\s*(\[[\s\S]*?\])\s*Task:", user)
            if match:
                candidates = json.loads(match.group(1))
        except Exception as exc:
            logger.warning("DynamicMockLLMClient: failed to parse candidates: %s", exc)

        top_k = 5
        try:
            match_k = re.search(r"Select the top (\d+) restaurants", user)
            if match_k:
                top_k = int(match_k.group(1))
        except Exception:
            pass

        selected = candidates[:top_k]
        recommendations = []
        for i, c in enumerate(selected):
            recommendations.append({
                "restaurant_id": c.get("id"),
                "rank": i + 1,
                "explanation": f"Recommended because it is a {c.get('budget_tier', 'medium')}-budget option offering {', '.join(c.get('cuisines', []))} cuisine in {c.get('location', '')} with a solid rating of {c.get('rating', 'N/A')}."
            })

        result = {
            "summary": f"Selected the top {len(selected)} restaurants matching your preferences.",
            "recommendations": recommendations
        }
        return json.dumps(result)


def get_llm_client() -> LLMClient:
    """Factory: Groq client for production, or mock client for testing/offline runs."""
    settings = get_settings()
    if settings.llm_provider.lower() == "mock":
        return DynamicMockLLMClient()
    return GroqLLMClient()

