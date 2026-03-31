#!/usr/bin/env python3
"""
Label finished matches in `match_predictions` by copying them to
`match_predictions_labeled` and marking originals as labeled.

This script now supports:
 - `--dump` fallback to process a local JSON dump when MongoDB is unavailable
 - `--output` to write labeled results to a JSON file
 - `--dry-run` to avoid DB writes (useful for testing)
 - `--limit` to limit processed documents
 - `--retries` to retry DB writes on transient errors

Usage examples:
  # normal run (requires Mongo):
  python3 backend/scripts/label_finished_matches.py

  # use a local dump and write output JSON
  python3 backend/scripts/label_finished_matches.py \
    --dump backend/sample_data/match_predictions_sample.json \
    --output specs/definir-metrics/labels_output.json
"""

import argparse
import datetime
import json
import logging
import os
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

# Accept a broader set of final-status markers across providers
FINISHED_STATUSES = ["FT", "AET", "PEN", "FT_PEN", "FINISHED", "FINAL", "ENDED", "post"]


def int_or_none(v):
    if v is None:
        return None
    try:
        return int(float(str(v).strip()))
    except Exception:
        return None


def load_from_dump(dump_path):
    with open(dump_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run_labeler_on_docs(docs, write_to_db=None, dry_run=False, retries=3, limit=None):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    processed = 0
    skipped = 0
    results = []

    for doc in docs:
        if limit and processed >= limit:
            break

        match_id = doc.get("match_id")
        data = doc.get("data", {})
        match = data.get("match", {}) or {}

        # robust extraction of final scores
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

        # alternative nested 'score' dict
        if (
            (home_goals is None or away_goals is None)
            and "score" in match
            and isinstance(match["score"], dict)
        ):
            home_goals = home_goals or match["score"].get("home")
            away_goals = away_goals or match["score"].get("away")

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
            "labeled_at": now_iso,
        }

        results.append(labeled_doc)

        # attempt DB writes unless dry-run or no DB provided
        if write_to_db and not dry_run:
            src_collection, target_collection = write_to_db
            # update labeled collection and mark original; retry on transient errors
            for attempt in range(1, retries + 1):
                try:
                    target_collection.update_one(
                        {"match_id": match_id}, {"$set": labeled_doc}, upsert=True
                    )
                    src_collection.update_one(
                        {"_id": doc.get("_id")},
                        {
                            "$set": {
                                "labeled": True,
                                "label": label,
                                "labeled_at": now_iso,
                            }
                        },
                    )
                    break
                except PyMongoError as e:
                    logging.warning(
                        "DB write failed (attempt %s/%s) for %s: %s",
                        attempt,
                        retries,
                        match_id,
                        e,
                    )
                    time.sleep(1 * attempt)

        processed += 1

    return processed, skipped, results


def main():
    parser = argparse.ArgumentParser(
        description="Label finished matches (with DB or dump fallback)"
    )
    parser.add_argument(
        "--dump",
        help="Path to JSON dump of match_predictions to use if Mongo is unavailable",
    )
    parser.add_argument(
        "--output",
        help="Write labeled results to this JSON file",
        default="specs/definir-metrics/labels_output.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write to DB; only produce output file",
    )
    parser.add_argument("--limit", type=int, help="Limit number of processed documents")
    parser.add_argument("--retries", type=int, default=3, help="Retries for DB writes")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="[labeler] %(asctime)s %(levelname)s: %(message)s"
    )

    uri = os.getenv("MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/")
    db_name = os.getenv("MONGO_DB_NAME", "bjj_betsports")

    docs = None
    write_to_db = None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        db = client[db_name]
        source = db["match_predictions"]
        target = db["match_predictions_labeled"]

        # Primary: status in canonical finished list
        # Fallback: presence of score fields (various provider schemas)
        score_presence_checks = [
            {"data.match.home_goals": {"$exists": True}},
            {"data.match.away_goals": {"$exists": True}},
            {"data.match.home_score": {"$exists": True}},
            {"data.match.away_score": {"$exists": True}},
            {"data.match.score": {"$exists": True}},
        ]

        query = {
            "$and": [
                {
                    "$or": [
                        {"data.match.status": {"$in": FINISHED_STATUSES}},
                        *score_presence_checks,
                    ]
                },
                {
                    "$or": [
                        {"labeled": {"$exists": False}},
                        {"labeled": {"$ne": True}},
                    ]
                },
            ]
        }

        docs = list(source.find(query))
        write_to_db = (source, target)
        logging.info("Connected to MongoDB; found %s candidate documents", len(docs))
    except ServerSelectionTimeoutError:
        logging.info("MongoDB not available; will try dump if provided")
    except Exception as exc:
        logging.warning("MongoDB error: %s", exc)

    if docs is None:
        # fallback to dump
        if args.dump and os.path.exists(args.dump):
            docs = load_from_dump(args.dump)
            logging.info("Loaded %s documents from dump %s", len(docs), args.dump)
        else:
            logging.error("No data source available (Mongo down and no dump). Exiting.")
            return

    processed, skipped, results = run_labeler_on_docs(
        docs,
        write_to_db=write_to_db,
        dry_run=args.dry_run,
        retries=args.retries,
        limit=args.limit,
    )

    # ensure output dir exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated_at": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "processed": processed,
                "skipped": skipped,
                "labeled": results,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    logging.info(
        "Processed %s matches, skipped %s. Output written to %s",
        processed,
        skipped,
        args.output,
    )


if __name__ == "__main__":
    main()
