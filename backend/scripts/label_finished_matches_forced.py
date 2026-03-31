#!/usr/bin/env python3
"""
Label matches that have final scores even if their `status` is not marked as finished.

This is a forced pass for cases where external data contains final scores
but the `match.status` wasn't updated to 'FT'. Use with caution.

Usage:
  python3 backend/scripts/label_finished_matches_forced.py
"""

import argparse
import datetime
import json
import os

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

FINISHED_STATUSES = ["FT", "AET", "PEN", "FT_PEN"]


def int_or_none(v):
    if v is None:
        return None
    try:
        return int(float(str(v).strip()))
    except Exception:
        return None


def load_from_dump(dump_path):
    with open(dump_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Expect a list of documents
    return data


def run_labeler_on_docs(docs, write_output=None, dry_run=False):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    processed = 0
    skipped = 0
    out = []

    for doc in docs:
        match_id = doc.get("match_id")
        data = doc.get("data", {})
        match = data.get("match", {}) or {}

        home_goals = (
            match.get("home_goals")
            if match.get("home_goals") is not None
            else match.get("home_score")
        )
        away_goals = (
            match.get("away_goals")
            if match.get("away_goals") is not None
            else match.get("away_score")
        )

        if home_goals is None and "score" in match and isinstance(match["score"], dict):
            home_goals = match["score"].get("home")
            away_goals = match["score"].get("away")

        h = int_or_none(home_goals)
        a = int_or_none(away_goals)

        if h is None or a is None:
            skipped += 1
            continue

        actual_home = 1 if h > a else 0
        actual_draw = 1 if h == a else 0
        actual_away = 1 if a > h else 0

        label = {
            "home_goals": h,
            "away_goals": a,
            "winner": "home" if actual_home else ("away" if actual_away else "draw"),
            "actual_home": actual_home,
            "actual_draw": actual_draw,
            "actual_away": actual_away,
        }

        labeled_doc = {
            "match_id": match_id,
            "league_id": doc.get("league_id"),
            "data": data,
            "label": label,
            "original_id": doc.get("_id"),
            "labeled_at": now,
        }

        out.append(labeled_doc)
        processed += 1

    if write_output:
        os.makedirs(os.path.dirname(write_output), exist_ok=True)
        with open(write_output, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "generated_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "labeled": out,
                },
                fh,
                indent=2,
                ensure_ascii=False,
            )

    return processed, skipped, out


def main():
    parser = argparse.ArgumentParser(
        description="Forced labeler: label matches with final scores"
    )
    parser.add_argument(
        "--dump",
        help="Path to JSON dump of match_predictions to use if Mongo is unavailable",
    )
    parser.add_argument(
        "--output",
        help="Write labeled output to this JSON file",
        default="specs/definir-metrics/labels_forced_output.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write to DB; only produce output file",
    )
    args = parser.parse_args()

    uri = os.getenv("MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/")
    db_name = os.getenv("MONGO_DB_NAME", "bjj_betsports")

    # Try connecting to Mongo; if fails and dump provided, use dump as fallback
    docs = None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        db = client[db_name]
        source = db["match_predictions"]
        # Use query similar to previous implementation
        query = {
            "$and": [
                {
                    "$or": [
                        {"data.match.status": {"$in": FINISHED_STATUSES}},
                        {
                            "$or": [
                                {"data.match.home_goals": {"$exists": True}},
                                {"data.match.home_score": {"$exists": True}},
                                {"data.match.away_goals": {"$exists": True}},
                                {"data.match.away_score": {"$exists": True}},
                            ]
                        },
                    ]
                },
                {"$or": [{"labeled": {"$exists": False}}, {"labeled": {"$ne": True}}]},
            ]
        }
        cursor = list(source.find(query))
        docs = cursor
    except ServerSelectionTimeoutError:
        print("Mongo not available; will try to use --dump if provided")
    except Exception as exc:
        print("Mongo error:", exc)

    if docs is None:
        if args.dump and os.path.exists(args.dump):
            docs = load_from_dump(args.dump)
        else:
            # Try default sample path
            sample_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "sample_data",
                "match_predictions_sample.json",
            )
            sample_path = os.path.normpath(sample_path)
            if os.path.exists(sample_path):
                docs = load_from_dump(sample_path)
            else:
                print(
                    "No data source available (Mongo down and no dump found). Exiting."
                )
                return

    processed, skipped, out = run_labeler_on_docs(
        docs, write_output=args.output, dry_run=args.dry_run
    )
    print(
        f"Processed {processed} matches, skipped {skipped}. "
        f"Output written to {args.output}"
    )


if __name__ == "__main__":
    main()
