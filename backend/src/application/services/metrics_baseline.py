"""
Minimal metrics baseline service

Computes simple baseline metrics (90-day window) from labeled predictions
persisted in the Explorer DB (MongoRepository.match_predictions).
"""

from datetime import timedelta
from typing import Any

from src.utils.time_utils import get_current_time


def compute_baseline(persistence_repo: Any, days: int = 90) -> dict[str, Any]:
    now = get_current_time()
    cutoff = now - timedelta(days=days)

    total = 0
    sum_confidence = 0.0

    cursor = persistence_repo.match_predictions.find({"labeled": True})
    for doc in cursor:
        labeled_at = doc.get("labeled_at")
        if not labeled_at:
            continue
        try:
            # Assume labeled_at is a datetime; otherwise try isoparse
            from datetime import datetime

            if isinstance(labeled_at, str):
                labeled_dt = datetime.fromisoformat(labeled_at)
            else:
                labeled_dt = labeled_at
        except Exception:
            continue

        if labeled_dt >= cutoff:
            total += 1
            try:
                conf = float(
                    doc.get("data", {}).get("prediction", {}).get("confidence", 0.0)
                )
            except Exception:
                conf = 0.0
            sum_confidence += conf

    avg_confidence = sum_confidence / total if total > 0 else 0.0

    return {
        "window_days": days,
        "total_labeled": total,
        "avg_confidence": round(avg_confidence, 4),
        "generated_at": now.isoformat(),
    }
