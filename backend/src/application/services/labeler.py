"""Labeler service: reconcile predictions with match results.

This is a modest, best-effort implementation that uses the MongoRepository API
when available. It supports dry-run mode which returns a report without
persisting changes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.utils.metrics import get_counter
from src.utils.time_utils import get_current_time

logger = logging.getLogger(__name__)

# Metrics
_LABELED_COUNTER = get_counter("labeler_labeled_total", "Total labeled predictions")


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def _extract_scores(match_obj: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    """Try several common keys to find home/away goals as ints or numeric strings."""
    if not isinstance(match_obj, dict):
        return (None, None)
    # common keys
    candidates = [
        ("home_goals", "away_goals"),
        ("home_score", "away_score"),
        ("score",),
    ]
    for cand in candidates:
        if len(cand) == 2 and cand[0] in match_obj and cand[1] in match_obj:
            try:
                return _to_int(match_obj[cand[0]]), _to_int(match_obj[cand[1]])
            except Exception:
                continue
        if cand[0] == "score":
            score_obj = match_obj.get("score")
            if isinstance(score_obj, dict):
                s: Dict[str, Any] = score_obj
                try:
                    return (
                        _to_int(s.get("home") or s.get("home_score")),
                        _to_int(s.get("away") or s.get("away_score")),
                    )
                except Exception:
                    continue
    return (None, None)


def _decide_label(home: Optional[int], away: Optional[int]) -> str:
    if home is None or away is None:
        return "na"
    if home > away:
        return "home_win"
    if home < away:
        return "away_win"
    return "draw"


def reconcile_predictions(
    persistence_repo: Any, window_days: int = 90, dry_run: bool = True
) -> Dict[str, Any]:
    """Reconcile predictions using available match data.

    Returns a report dictionary with counts and a sample of audit entries.
    """
    cursor = persistence_repo.match_predictions.find({})
    labeled = 0
    skipped = 0
    audits: List[Dict[str, Any]] = []

    for doc in cursor:
        try:
            if not isinstance(doc, dict):
                skipped += 1
                continue
            # Skip if already labeled
            if doc.get("labeled"):
                skipped += 1
                continue

            data: Dict[str, Any] = doc.get("data") or {}
            match_obj = data.get("match") or data.get("match_data")
            if not match_obj or not isinstance(match_obj, dict):
                # no match info or unexpected shape; skip
                skipped += 1
                continue

            # Only reconcile finished matches (best-effort)
            status = (match_obj.get("status") or "").upper()
            if status not in ("FT", "F", "FIN", "FINISHED") and not match_obj.get(
                "home_goals"
            ):
                skipped += 1
                continue

            home_goal, away_goal = _extract_scores(match_obj)
            label = _decide_label(home_goal, away_goal)

            prediction = data.get("prediction") or {}
            audit = {
                "prediction_id": doc.get("_id") or doc.get("match_id"),
                "match_id": doc.get("match_id"),
                "matching_strategy": "match_obj_internal",
                "confidence": prediction.get("confidence"),
                "label": label,
                "timestamp": get_current_time().isoformat(),
            }

            audits.append(audit)

            if not dry_run:
                # Persist label on the prediction doc
                persistence_repo.match_predictions.update_one(
                    {"match_id": doc.get("match_id")},
                    {
                        "$set": {
                            "labeled": True,
                            "label": label,
                            "labeled_at": get_current_time(),
                        }
                    },
                )
                # Insert audit
                try:
                    persistence_repo.db["labeling_audit"].insert_one(audit)
                except Exception:
                    logger.exception(
                        "Failed to write labeling_audit for %s", doc.get("match_id")
                    )
                labeled += 1
                try:
                    _LABELED_COUNTER.inc()
                except Exception:
                    pass
            else:
                # dry-run; just count as would-be labeled
                labeled += 1
        except Exception:
            logger.exception(
                "Error while reconciling prediction: %s", doc.get("match_id")
            )
            skipped += 1

    return {
        "window_days": window_days,
        "labeled_count": labeled,
        "skipped_count": skipped,
        "sample_audits": audits[:50],
    }
