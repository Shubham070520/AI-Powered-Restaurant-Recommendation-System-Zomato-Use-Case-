"""Streamlit UI for restaurant recommendations (Phase 5)."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path to allow src.* imports when run via Streamlit
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from collections import Counter
from typing import Optional

import streamlit as st
from pydantic import ValidationError

from src.config import get_settings
from src.data.store import RestaurantStore
from src.llm.client import LLMClientError
from src.models.preferences import UserPreferences
from src.models.recommendation import RecommendationResponse
from src.services.recommender import RecommendationError, get_recommendations


@st.cache_resource(show_spinner="Loading restaurant dataset…")
def _cached_store() -> RestaurantStore:
    from src.data.store import get_store

    return get_store()


def _top_cities(store: RestaurantStore, limit: int = 25) -> list[str]:
    counts = Counter(r.location for r in store.get_all())
    return [city for city, _ in counts.most_common(limit)]


def _render_sidebar(store: RestaurantStore) -> None:
    settings = get_settings()
    st.sidebar.header("About")
    st.sidebar.caption(
        "Structured filters narrow the list; **Groq** ranks and explains the best matches."
    )
    st.sidebar.metric("Restaurants loaded", f"{len(store.get_all()):,}")
    key_ok = bool(settings.llm_api_key and settings.llm_api_key.strip())
    st.sidebar.metric("Groq API key", "Configured" if key_ok else "Missing")
    if not key_ok:
        st.sidebar.warning("Add `LLM_API_KEY` to `.env` for live recommendations.")
    st.sidebar.divider()
    st.sidebar.caption(f"Model: `{settings.llm_model}`")


def _build_preferences_from_form() -> Optional[UserPreferences]:
    cities = _top_cities(_cached_store())
    with st.form("preferences_form"):
        st.subheader("Your preferences")
        col1, col2 = st.columns(2)

        with col1:
            city_choice = st.selectbox(
                "Location",
                options=cities,
                index=cities.index("Bangalore") if "Bangalore" in cities else 0,
                help="City extracted from the dataset (mostly Bangalore).",
            )
            custom_city = st.text_input(
                "Or enter another location",
                placeholder="e.g. Bangalore",
            )
            location = (custom_city.strip() or city_choice).strip()

            budget = st.selectbox(
                "Budget",
                options=["low", "medium", "high"],
                index=1,
            )
            cuisine = st.text_input(
                "Cuisine (optional)",
                placeholder="e.g. Italian, Chinese",
            )

        with col2:
            min_rating = st.slider(
                "Minimum rating",
                min_value=0.0,
                max_value=5.0,
                value=0.0,
                step=0.5,
                help="Set above 0 to require a rating.",
            )
            top_k = st.number_input(
                "Top K results",
                min_value=1,
                max_value=10,
                value=5,
                step=1,
            )
            additional = st.text_input(
                "Additional preferences (optional)",
                placeholder="family-friendly, quick service",
                help="Comma-separated; used in AI explanations.",
            )

        submitted = st.form_submit_button(
            "Get recommendations",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return None

    additional_list = [p.strip() for p in additional.split(",") if p.strip()]
    return UserPreferences(
        location=location,
        budget=budget,  # type: ignore[arg-type]
        cuisine=cuisine or None,
        min_rating=min_rating if min_rating > 0 else None,
        additional_preferences=additional_list,
        top_k=int(top_k),
    )


def _render_results(response: RecommendationResponse) -> None:
    if response.message and not response.recommendations:
        st.warning(response.message)
        return

    if response.summary:
        st.success(response.summary)

    meta = response.meta
    st.caption(
        f"Considered **{meta.candidates_considered}** candidates "
        f"(**{meta.total_matched}** matched filters"
        + (", truncated for AI" if meta.truncated else "")
        + ")"
        + (
            f" · Groq `{meta.model}` · {meta.llm_latency_ms:.0f} ms"
            if meta.llm_latency_ms is not None
            else ""
        )
    )

    for item in response.recommendations:
        cuisines = ", ".join(item.cuisines) if item.cuisines else "—"
        rating = f"{item.rating:.1f}" if item.rating is not None else "N/A"
        cost = (
            f"₹{item.estimated_cost_for_two:,}"
            if item.estimated_cost_for_two is not None
            else "N/A"
        )
        tier = item.budget_tier or "—"

        with st.expander(f"#{item.rank} · {item.name}", expanded=item.rank <= 3):
            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**Cuisine:** {cuisines}")
            col_b.markdown(f"**Rating:** {rating}")
            col_c.markdown(f"**Cost for two:** {cost}")
            st.markdown(f"**Location:** {item.location} · **Budget tier:** {tier}")
            st.markdown(f"**Why this pick:** {item.explanation}")


def run() -> None:
    st.set_page_config(
        page_title="Zomato AI Recommendations",
        page_icon="🍽️",
        layout="wide",
    )
    st.title("AI Restaurant Recommendations")
    st.markdown(
        "Find restaurants that match your **location**, **budget**, and **taste** — "
        "with AI-powered ranking and explanations."
    )

    try:
        store = _cached_store()
    except Exception as exc:
        st.error(
            "Failed to load the restaurant dataset. Check your network or "
            "`DATA_CACHE_PATH` in `.env`."
        )
        st.exception(exc)
        return

    _render_sidebar(store)

    preferences = _build_preferences_from_form()
    if preferences is None:
        st.info("Set your preferences above and click **Get recommendations**.")
        with st.expander("Example search"):
            st.markdown(
                "- **Location:** Bangalore  \n"
                "- **Budget:** medium  \n"
                "- **Cuisine:** Italian  \n"
                "- **Min rating:** 4.0"
            )
        return

    with st.spinner("Filtering restaurants and asking Groq for rankings…"):
        try:
            response = get_recommendations(preferences, store=store)
        except ValidationError as exc:
            st.error("Invalid preferences. Please check your inputs.")
            st.json(exc.errors())
            return
        except LLMClientError as exc:
            st.error(str(exc))
            return
        except RecommendationError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error("Something went wrong. Please try again.")
            st.exception(exc)
            return

    st.divider()
    _render_results(response)


if __name__ == "__main__":
    run()
