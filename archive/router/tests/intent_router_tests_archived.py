"""Unit tests for the text-only intent router."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.intent_router import (  # noqa: E402
    INTENT_COMPARISON,
    INTENT_COUNTING,
    INTENT_MULTI_HOP,
    INTENT_RANKING,
    ROUTE_C1,
    ROUTE_C3,
    route_question,
)


def test_ranking_override_beats_counting() -> None:
    q = "Rank the countries by number of medals from highest to lowest."
    d = route_question(q)
    assert d.intent == INTENT_RANKING
    assert d.route_model == ROUTE_C3
    assert d.confidence == 1.0
    assert d.reason.startswith("RANK_OVERRIDE")


def test_non_ranking_counting_stays_c1_with_base_reason() -> None:
    q = "How many countries have GDP above 500 billion?"
    d = route_question(q)
    assert d.intent == INTENT_COUNTING
    assert d.route_model == ROUTE_C1
    assert d.reason.startswith("BASE_INTENT_COUNTING")


def test_multihop_promotion_reachable_for_non_multihop_base_intent() -> None:
    q = (
        "Compare sales and profits with both metrics for each region "
        "and find the total of eligible rows."
    )
    d = route_question(q, mh_conf_threshold=0.45)
    assert d.intent in (INTENT_COMPARISON, INTENT_MULTI_HOP)
    assert d.route_model == ROUTE_C3
    assert d.reason.startswith("MH_PROMOTION")


def test_low_confidence_comparison_stays_base_c1() -> None:
    q = "Which is higher, 2020 or 2021?"
    d = route_question(q, mh_conf_threshold=0.45)
    assert d.intent == INTENT_COMPARISON
    assert d.route_model == ROUTE_C1
    assert d.reason.startswith("BASE_INTENT_COMPARISON")


def test_default_threshold_045_promotes_but_055_does_not() -> None:
    q = "Compare higher sales and profits with both metrics."
    low = route_question(q)  # default threshold 0.45
    high = route_question(q, mh_conf_threshold=0.55)

    assert low.route_model == ROUTE_C3
    assert low.reason.startswith("MH_PROMOTION")
    assert high.route_model == ROUTE_C1
    assert high.reason.startswith("BASE_INTENT_COMPARISON")


def test_determinism_for_reason_and_route() -> None:
    q = "Rank the products in descending order by number of units sold."
    runs = [route_question(q) for _ in range(5)]
    assert len({r.intent for r in runs}) == 1
    assert len({r.route_model for r in runs}) == 1
    assert len({r.confidence for r in runs}) == 1
    assert len({r.reason for r in runs}) == 1
