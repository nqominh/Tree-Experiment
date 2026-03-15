"""Utilities for answer normalization and EM scoring."""

from __future__ import annotations

import re


def _process_decimal(value: str) -> str:
    """Normalize number format without forced rounding."""
    try:
        numeric = float(value)
        if numeric == int(numeric):
            return str(int(numeric))
        return str(numeric)
    except (ValueError, OverflowError):
        return value


def normalize_answer_for_em(value: str) -> str:
    """Normalize free-form text for exact-match style evaluation."""
    normalized = value.strip().strip('"').strip("'").rstrip(".").strip()
    normalized = normalized.replace("$", "").replace("%", "").replace(",", "")
    normalized = re.sub(r"\b(a|an|the)\b", " ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = " ".join(normalized.lower().split())
    return _process_decimal(normalized)


def exact_match_with_normalization(predicted: str, label: str) -> int:
    """Return EM=1 if raw match or normalized match succeeds, else 0."""
    if not predicted.strip():
        return 0
    if predicted.strip().lower() == label.strip().lower():
        return 1

    normalized_pred = normalize_answer_for_em(predicted)
    normalized_label = normalize_answer_for_em(label)
    return 1 if normalized_pred == normalized_label else 0
