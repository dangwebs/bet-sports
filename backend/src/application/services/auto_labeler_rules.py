"""Market-specific label derivation helpers for the AutoLabeler.

This module contains small, well-tested functions that derive per-market
labels (winner, over/under) from a persisted prediction document and the
final match object returned by external data sources.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    """Robust getter that works with objects or dicts."""
    for name in names:
        if obj is None:
            return default
        # dict-like
        try:
            if isinstance(obj, dict) and name in obj:
                return obj[name]
        except Exception:
            pass
        # attr-like
        try:
            val = getattr(obj, name)
            return val
        except Exception:
            pass
    return default


def get_actual_outcome(match: Any) -> Optional[str]:
    """Return actual outcome string: 'home_win'|'draw'|'away_win' or None."""
    home = _get(match, "home_goals", "home_score", "home")
    away = _get(match, "away_goals", "away_score", "away")
    try:
        if home is None or away is None:
            return None
        home_i = int(home)
        away_i = int(away)
    except Exception:
        return None
    if home_i > away_i:
        return "home_win"
    if home_i < away_i:
        return "away_win"
    return "draw"


def derive_market_labels(doc: Dict[str, Any], match: Any) -> Dict[str, Any]:
    """Derive simple market-level labels from a prediction document + match.

    Currently derives:
    - winner: predicted probability for the actual outcome + is_correct flag
    - over_25: predicted probability + actual boolean

    The function is defensive: if prediction probabilities are missing
    for a market, that market is omitted from the result.
    """
    result: Dict[str, Any] = {}

    pred = doc.get("data", {}).get("prediction", {}) if isinstance(doc, dict) else {}

    # Winner market
    home_p = pred.get("home_win_probability")
    draw_p = pred.get("draw_probability")
    away_p = pred.get("away_win_probability")
    # Prefer match info embedded in the document when available
    doc_match = None
    if isinstance(doc, dict):
        doc_match = doc.get("data", {}).get("match")
    actual = get_actual_outcome(doc_match) or get_actual_outcome(match)
    if actual:
        # predicted probability for actual outcome (if available)
        prob_map = {"home_win": home_p, "draw": draw_p, "away_win": away_p}
        pred_prob = prob_map.get(actual)
        # determine predicted label when full distribution present
        predicted_label = None
        if all(p is not None for p in (home_p, draw_p, away_p)):
            max_p = max(home_p, draw_p, away_p)
            if max_p == home_p:
                predicted_label = "home_win"
            elif max_p == draw_p:
                predicted_label = "draw"
            else:
                predicted_label = "away_win"

        result["winner"] = {
            "actual": actual,
            "predicted_probability": pred_prob,
            "predicted_label": predicted_label,
            "is_correct": (predicted_label == actual) if predicted_label else None,
        }

    # Over/Under 2.5 market
    over_p = pred.get("over_25_probability")
    if over_p is not None:
        # compute actual total goals
        home = _get(match, "home_goals", "home_score", "home")
        away = _get(match, "away_goals", "away_score", "away")
        try:
            total = int(home) + int(away)
            actual_over = total >= 3
        except Exception:
            actual_over = None

        result["over_25"] = {
            "predicted_probability": over_p,
            "actual_over": actual_over,
        }

    return result
