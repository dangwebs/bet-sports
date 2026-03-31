#!/usr/bin/env python3
"""Simple labeler CLI used by admin endpoints and cron jobs.

This script supports a `--dry-run` mode which will not persist changes and
will emit a small JSON/CSV report.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List


def load_sample_predictions() -> List[Dict[str, Any]]:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    sample_path = os.path.join(
        repo_root, "backend", "sample_data", "match_predictions_sample.json"
    )
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return []


def extract_scores(match_obj: Dict[str, Any]):
    if not isinstance(match_obj, dict):
        return (None, None)
    # common keys
    if "home_goals" in match_obj and "away_goals" in match_obj:
        try:
            return int(match_obj.get("home_goals")), int(match_obj.get("away_goals"))
        except Exception:
            pass
    if "score" in match_obj and isinstance(match_obj.get("score"), dict):
        s = match_obj.get("score")
        try:
            return int(s.get("home") or s.get("home_score")), int(
                s.get("away") or s.get("away_score")
            )
        except Exception:
            pass
    # fallback
    return (None, None)


def decide_label(home, away):
    if home is None or away is None:
        return "na"
    if home > away:
        return "home_win"
    if home < away:
        return "away_win"
    return "draw"


def main():
    parser = argparse.ArgumentParser(description="Labeler dry-run/persist CLI")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist changes")
    parser.add_argument("--window", default="90d", help="Window (e.g. 90d)")
    args = parser.parse_args()

    # Simple data source: sample file. If Mongo is available in environment,
    # the admin endpoints will call the same logic via application service.
    preds = load_sample_predictions()
    if not preds:
        print(json.dumps({"error": "no sample data found"}))
        return

    audits = []
    for p in preds:
        match_obj = p.get("data", {}).get("match") or {}
        home, away = extract_scores(match_obj)
        label = decide_label(home, away)
        audits.append(
            {
                "prediction_id": p.get("_id"),
                "match_id": p.get("match_id"),
                "label": label,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    # Emit report to stdout
    report = {"window": args.window, "count": len(audits), "audits": audits}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
