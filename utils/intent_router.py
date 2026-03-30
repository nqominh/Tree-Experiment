"""
intent_router.py — Deterministic, confidence-gated intent router for Table QA.

Classifies a question into an intent category and routes it to the
appropriate experimental condition (C1 = Vanilla HTML, C3 = Schema + HTML).

Usage:
    from utils.intent_router import route_question

    decision = route_question("Which country ranked highest in GDP?")
    print(decision.intent, decision.route_model, decision.confidence)
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Route taxonomy constants
# ---------------------------------------------------------------------------

INTENT_COUNTING = "COUNTING"
INTENT_RANKING = "RANKING"
INTENT_COMPARISON = "COMPARISON"
INTENT_MULTI_HOP = "MULTI_HOP"
INTENT_CALCULATION = "CALCULATION"

ROUTE_C1 = "C1"
ROUTE_C3 = "C3"

# Precedence order: first match wins.
# Rule: COUNTING must win over CALCULATION when both appear.
INTENT_PRECEDENCE = [
    INTENT_COUNTING,
    INTENT_RANKING,
    INTENT_COMPARISON,
    INTENT_MULTI_HOP,
    INTENT_CALCULATION,
]

# ---------------------------------------------------------------------------
# Trigger dictionaries
# ---------------------------------------------------------------------------

# Each value is a list of trigger phrases.  Multi-word phrases are checked
# first via substring matching; single words via token membership.

RANKING_TRIGGERS: list[str] = [
    "rank", "ranking", "top", "top-k", "bottom", "highest", "lowest",
    "sort", "sorted", "order", "ascending", "descending",
    "largest", "smallest", "most", "least", "greatest", "fewest",
]

COUNTING_TRIGGERS: list[str] = [
    "how many", "count", "number of", "cardinality",
]

CALCULATION_TRIGGERS: list[str] = [
    "sum", "total", "average", "mean", "difference",
    "minus", "plus", "ratio", "percent", "percentage",
    "multiply", "divide", "subtract", "add",
]

COMPARISON_TRIGGERS: list[str] = [
    "compare", "comparison", "which is higher", "which is lower",
    "larger", "smaller", "greater", "less", "versus", "than",
    "higher", "lower", "more", "fewer", "exceed",
]

MULTI_HOP_TRIGGERS: list[str] = [
    "if", "if then", "conditional", "suppose", "assume",
    "what would", "under condition", "given that", "then what",
    "after", "then",
    "combined", "combined with", "across", "would be", "would have", "total of",
]

RANKING_OVERRIDE_TRIGGERS: list[str] = [
    "rank", "ranking", "ranked",
    "from highest to lowest", "from lowest to highest",
    "in descending order", "in ascending order",
    "sorted by", "order by",
]

# ---------------------------------------------------------------------------
# Multi-hop confidence feature markers
# ---------------------------------------------------------------------------

CONSTRAINT_MARKERS: list[str] = [
    "and", "both", "with", "where", "excluding", "not",
    "at least", "at most", "only", "except", "but not",
]

OPERATOR_GROUPS: dict[str, list[str]] = {
    "filter": ["where", "excluding", "only", "except", "not", "but not", "without"],
    "aggregate": ["sum", "total", "total of", "combined", "average", "mean", "count", "how many"],
    "compare": ["larger", "smaller", "greater", "less", "more", "fewer", "higher", "lower", "than"],
    "rank": ["rank", "top", "bottom", "highest", "lowest", "most", "least"],
    "arithmetic": ["difference", "minus", "plus", "ratio", "multiply", "divide", "subtract", "add", "percent"],
}

CROSS_REFERENCE_MARKERS: list[str] = [
    "same row", "corresponding", "per category",
    "compared with", "between", "then use that",
    "respectively", "across", "for each",
]


# ---------------------------------------------------------------------------
# Output data class
# ---------------------------------------------------------------------------

@dataclass
class RouteDecision:
    """Result of the intent router."""
    intent: str
    route_model: str  # "C1" or "C3"
    confidence: float
    reason: str
    policy_version: str = ""

    # Internal diagnostics (not written to CSV by default)
    match_counts: dict[str, int] = field(default_factory=dict)
    mh_features: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def _normalize_question(text: str) -> str:
    """Lowercase, collapse whitespace, simplify punctuation."""
    q = text.lower().strip()
    # collapse whitespace
    q = re.sub(r"\s+", " ", q)
    return q


def _tokenize(text: str) -> list[str]:
    """Split normalized text into tokens (words)."""
    # Remove punctuation then split
    cleaned = text.translate(str.maketrans("", "", string.punctuation))
    return cleaned.split()


# ---------------------------------------------------------------------------
# Trigger matching
# ---------------------------------------------------------------------------

def _count_triggers(q_norm: str, tokens: list[str], triggers: list[str]) -> int:
    """Count how many triggers match the question.

    Multi-word triggers are checked as substrings of q_norm.
    Single-word triggers are checked via token membership.
    """
    count = 0
    for trigger in triggers:
        if " " in trigger:
            # multi-word: substring match
            if trigger in q_norm:
                count += 1
        else:
            # single word: token membership
            if trigger in tokens:
                count += 1
    return count


def _collect_matched_triggers(q_norm: str, tokens: list[str], triggers: list[str]) -> list[str]:
    """Return matched triggers preserving trigger list order."""
    matched: list[str] = []
    for trigger in triggers:
        if " " in trigger:
            if trigger in q_norm:
                matched.append(trigger)
        else:
            if trigger in tokens:
                matched.append(trigger)
    return matched


# ---------------------------------------------------------------------------
# Multi-hop confidence scoring
# ---------------------------------------------------------------------------

def _compute_multihop_confidence(q_norm: str, tokens: list[str]) -> tuple[float, dict[str, float]]:
    """Compute confidence that a question is truly multi-hop.

    Returns (conf_mh, feature_dict) where conf_mh ∈ [0, 1].
    """
    # 1. Constraint markers
    constraint_count = 0
    for marker in CONSTRAINT_MARKERS:
        if " " in marker:
            if marker in q_norm:
                constraint_count += 1
        else:
            if marker in tokens:
                constraint_count += 1

    # 2. Distinct operator groups present
    distinct_groups = 0
    for group_name, group_triggers in OPERATOR_GROUPS.items():
        for trigger in group_triggers:
            if " " in trigger:
                if trigger in q_norm:
                    distinct_groups += 1
                    break
            else:
                if trigger in tokens:
                    distinct_groups += 1
                    break

    # 3. Cross-reference markers
    cross_ref_count = 0
    for marker in CROSS_REFERENCE_MARKERS:
        if marker in q_norm:
            cross_ref_count += 1

    # Normalized components
    s_constraints = min(1.0, constraint_count / 3)
    s_operators = min(1.0, distinct_groups / 3)
    s_cross_ref = min(1.0, cross_ref_count / 2)

    conf_mh = 0.4 * s_constraints + 0.3 * s_operators + 0.3 * s_cross_ref

    features = {
        "constraint_marker_count": constraint_count,
        "distinct_operator_group_count": distinct_groups,
        "cross_reference_marker_count": cross_ref_count,
        "s_constraints": round(s_constraints, 3),
        "s_operators": round(s_operators, 3),
        "s_cross_ref": round(s_cross_ref, 3),
        "conf_mh": round(conf_mh, 3),
    }

    return conf_mh, features


# ---------------------------------------------------------------------------
# Main routing function
# ---------------------------------------------------------------------------

def route_question(
    question_text: str,
    policy_version: str = "router_v1_2026_03_29",
    mh_conf_threshold: float = 0.45,
    subqtype_hint: str = "",
) -> RouteDecision:
    """Classify a question and return the routing decision.

    Parameters
    ----------
    question_text : str
        The raw question string.
    policy_version : str
        Immutable policy version string for audit trail.
    mh_conf_threshold : float
        Confidence threshold for promoting multi-hop to C3.
    subqtype_hint : str
        Optional subtype hint from metadata (currently unused but reserved).

    Returns
    -------
    RouteDecision
        Contains intent, route_model (C1/C3), confidence, and reason.
    """
    q_norm = _normalize_question(question_text)
    tokens = _tokenize(q_norm)

    # Ranking-first hard override to avoid COUNTING precedence hijacking
    override_cues = _collect_matched_triggers(q_norm, tokens, RANKING_OVERRIDE_TRIGGERS)
    if override_cues:
        counts = {
            INTENT_COUNTING: _count_triggers(q_norm, tokens, COUNTING_TRIGGERS),
            INTENT_RANKING: _count_triggers(q_norm, tokens, RANKING_TRIGGERS),
            INTENT_COMPARISON: _count_triggers(q_norm, tokens, COMPARISON_TRIGGERS),
            INTENT_MULTI_HOP: _count_triggers(q_norm, tokens, MULTI_HOP_TRIGGERS),
            INTENT_CALCULATION: _count_triggers(q_norm, tokens, CALCULATION_TRIGGERS),
        }
        return RouteDecision(
            intent=INTENT_RANKING,
            route_model=ROUTE_C3,
            confidence=1.0,
            reason=f"RANK_OVERRIDE cues: {override_cues}",
            policy_version=policy_version,
            match_counts=counts,
            mh_features={},
        )

    # Count triggers per intent
    counts = {
        INTENT_COUNTING: _count_triggers(q_norm, tokens, COUNTING_TRIGGERS),
        INTENT_RANKING: _count_triggers(q_norm, tokens, RANKING_TRIGGERS),
        INTENT_COMPARISON: _count_triggers(q_norm, tokens, COMPARISON_TRIGGERS),
        INTENT_MULTI_HOP: _count_triggers(q_norm, tokens, MULTI_HOP_TRIGGERS),
        INTENT_CALCULATION: _count_triggers(q_norm, tokens, CALCULATION_TRIGGERS),
    }

    # Resolve intent by precedence: first intent with count > 0 wins
    route_intent = INTENT_CALCULATION
    matched_cues: list[str] = []

    for intent in INTENT_PRECEDENCE:
        if counts.get(intent, 0) > 0:
            route_intent = intent
            # Collect matched triggers for reason string
            if intent == INTENT_COUNTING:
                trigger_list = COUNTING_TRIGGERS
            elif intent == INTENT_RANKING:
                trigger_list = RANKING_TRIGGERS
            elif intent == INTENT_COMPARISON:
                trigger_list = COMPARISON_TRIGGERS
            elif intent == INTENT_MULTI_HOP:
                trigger_list = MULTI_HOP_TRIGGERS
            elif intent == INTENT_CALCULATION:
                trigger_list = CALCULATION_TRIGGERS
            else:
                trigger_list = []

            matched_cues = _collect_matched_triggers(q_norm, tokens, trigger_list)
            break

    # Stage 2: evaluate multi-hop confidence regardless of base intent.
    conf_mh, mh_features = _compute_multihop_confidence(q_norm, tokens)

    # Stage 3: apply routing decision with explicit reason labels.
    if route_intent == INTENT_RANKING:
        route_model = ROUTE_C3
        confidence = 1.0
        reason = f"BASE_INTENT_RANKING cues: {matched_cues}"
    elif conf_mh >= mh_conf_threshold:
        route_model = ROUTE_C3
        confidence = conf_mh
        reason = (
            f"MH_PROMOTION(conf={conf_mh:.2f}, threshold={mh_conf_threshold:.2f}, "
            f"base_intent={route_intent}, cues={matched_cues})"
        )
    elif route_intent in (INTENT_COUNTING, INTENT_CALCULATION, INTENT_COMPARISON, INTENT_MULTI_HOP):
        route_model = ROUTE_C1
        confidence = conf_mh
        reason = f"BASE_INTENT_{route_intent} cues: {matched_cues}"
    else:
        route_model = ROUTE_C1
        confidence = conf_mh
        reason = "BASE_INTENT_FALLBACK"

    return RouteDecision(
        intent=route_intent,
        route_model=route_model,
        confidence=round(confidence, 3),
        reason=reason,
        policy_version=policy_version,
        match_counts=counts,
        mh_features=mh_features,
    )
