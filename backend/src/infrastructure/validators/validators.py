"""Data sanity validators and helpers.

These are intentionally conservative and dependency-light: they avoid optional
heavy libraries and provide safe fallbacks so the API can run in minimal
environments.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _parse_iso(dt_str: str) -> Optional[datetime]:
    """Try to parse an ISO-like datetime string into an aware UTC datetime.

    Uses builtin `fromisoformat` as primary path; falls back to simple
    normalization if it fails.
    """
    if not dt_str:
        return None
    try:
        # Python's fromisoformat handles offsets in recent versions
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            # treat naive as UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        # Best-effort: try to strip fractional seconds / Z suffix
        try:
            if dt_str.endswith("Z"):
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc)
        except Exception:
            return None
    # Ensure an explicit None return for all code paths
    return None


def normalize_timestamp_to_iso(ts: str) -> str:
    """Return a normalized ISO8601 UTC timestamp string or raise ValueError."""
    dt = _parse_iso(ts)
    if not dt:
        raise ValueError(f"Invalid timestamp: {ts}")
    return dt.isoformat()


def validate_probability(value: Any) -> float:
    """Ensure a numeric probability in [0,1]. Returns the float value or raises."""
    try:
        f = float(value)
    except Exception:
        raise ValueError(f"Not a float: {value}")
    if f < 0.0 or f > 1.0:
        raise ValueError(f"Probability out of range [0,1]: {f}")
    return f


def validate_prediction_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a minimal prediction payload shape and normalize some fields.

    - Ensures `created_at` is ISO string
    - Ensures probabilities are in [0,1]

    This function performs best-effort normalization and raises ValueError on
    clearly invalid inputs.
    """
    if not isinstance(payload, dict):
        raise ValueError("Prediction payload must be a dict")

    pred = payload.get("prediction") or payload

    # Normalize created_at
    created = pred.get("created_at")
    if created:
        try:
            pred["created_at"] = normalize_timestamp_to_iso(created)
        except ValueError:
            raise

    # Normalize confidence / probabilities if present
    # Common keys: confidence, home_win_probability, away_win_probability
    for key in ("confidence", "home_win_probability", "away_win_probability"):
        if key in pred and pred[key] is not None:
            pred[key] = validate_probability(pred[key])

    return payload


def load_team_aliases() -> Dict[str, str]:
    """Load canonical team aliases from the repository data folder.

    Returns an empty dict if the file can't be found — caller should handle
    fallbacks.
    """
    try:
        repo_root = Path(__file__).resolve().parents[3]
        aliases_path = repo_root / "backend" / "data" / "team_short_names.json"
        if aliases_path.exists():
            with aliases_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
                return {}
    except Exception as exc:
        logger.debug("Failed to load team aliases: %s", exc)
    return {}
