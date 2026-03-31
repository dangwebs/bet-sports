#!/usr/bin/env python3
"""
Update stored match predictions with final match results from data sources.

Checks recent finished matches across available sources and, when a
corresponding `match_id` exists in the `match_predictions` collection,
updates the `data.match` fields (status, home_goals, away_goals).

This helps the `label_finished_matches.py` script to find candidates
without relying solely on upstream status strings.

Usage:
  python3 backend/scripts/update_predictions_with_results.py --days-back 3

Options:
  --days-back N   Look back N days for finished matches (default: 3)
  --dry-run       Do not write to DB; only print planned updates
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# allow running from repo root
sys.path.append(os.getcwd())

from src.dependencies import get_match_aggregator_service, get_persistence_repository
from src.domain.constants import LEAGUES_METADATA

logging.basicConfig(
    level=logging.INFO, format="[updater] %(asctime)s %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def gather_finished_matches(aggregator, league_id: str, days_back: int):
    """Gather finished matches for a league from available sources."""
    now = datetime.utcnow()
    date_to = now.strftime("%Y-%m-%d")
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

    matches = []

    # Primary: Football-Data.org (if configured)
    try:
        if aggregator.football_data_org.is_configured:
            fd_matches = await aggregator.football_data_org.get_finished_matches(
                date_from=date_from, date_to=date_to, league_codes=[league_id]
            )
            matches.extend(fd_matches or [])
    except Exception as e:
        logger.debug("Football-Data.org fetch failed for %s: %s", league_id, e)

    # ESPN (recent finished matches)
    try:
        espn_matches = await aggregator.espn.get_finished_matches(
            league_codes=[league_id], days_back=days_back
        )
        matches.extend(espn_matches or [])
    except Exception as e:
        logger.debug("ESPN fetch failed for %s: %s", league_id, e)

    # TheSportsDB (past events)
    try:
        ts_matches = await aggregator.thesportsdb.get_past_events(
            league_id, max_events=200
        )
        matches.extend(ts_matches or [])
    except Exception as e:
        logger.debug("TheSportsDB fetch failed for %s: %s", league_id, e)

    # Remove duplicates by match.id
    unique = {}
    for m in matches:
        if not m or not getattr(m, "id", None):
            continue
        unique[m.id] = m

    return list(unique.values())


async def main():  # noqa: C901
    parser = argparse.ArgumentParser(
        description="Update predictions with final results"
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=3,
        help="Days to look back for finished matches",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not write to DB; only show changes"
    )
    parser.add_argument(
        "--leagues",
        type=str,
        default=None,
        help="Comma-separated league ids to limit (e.g. D1,E0)",
    )
    args = parser.parse_args()

    aggregator = get_match_aggregator_service()
    repo = get_persistence_repository()

    updated = 0
    not_found = 0
    total_checked = 0

    if args.leagues:
        league_ids = [lid.strip() for lid in args.leagues.split(",") if lid.strip()]
    else:
        league_ids = list(LEAGUES_METADATA.keys())

    for league_id in league_ids:
        logger.info(
            "Checking league %s for finished matches (last %s days)",
            league_id,
            args.days_back,
        )
        try:
            matches = await gather_finished_matches(
                aggregator, league_id, args.days_back
            )
        except Exception as e:
            logger.warning("Failed to gather finished matches for %s: %s", league_id, e)
            continue

        logger.info("Found %s finished matches for league %s", len(matches), league_id)

        for m in matches:
            total_checked += 1
            match_id = getattr(m, "id", None)
            if not match_id:
                continue

            # try flexible matching: normalize to string and try variants
            mid = str(match_id)
            candidate_ids = [mid]
            if mid.isdigit():
                candidate_ids.append(f"espn_{mid}")
            if mid.startswith("espn_"):
                candidate_ids.append(mid.split("espn_")[-1])
            candidate_ids.append(mid.replace(" ", "").replace("-", "_"))

            doc = None
            for cid in candidate_ids:
                doc = repo.match_predictions.find_one({"match_id": cid})
                if doc:
                    break
            if not doc:
                not_found += 1
                logger.debug("No prediction found for match_id=%s", match_id)
                continue

            data = doc.get("data", {}) or {}
            match_node = data.get("match", {}) or {}

            # Update fields where present
            changed = False
            if getattr(m, "status", None) and match_node.get("status") != m.status:
                match_node["status"] = m.status
                changed = True

            if getattr(m, "home_goals", None) is not None:
                # allow update even if previously None
                if match_node.get("home_goals") != m.home_goals:
                    match_node["home_goals"] = m.home_goals
                    changed = True

            if getattr(m, "away_goals", None) is not None:
                if match_node.get("away_goals") != m.away_goals:
                    match_node["away_goals"] = m.away_goals
                    changed = True

            # If source uses nested 'score' dict, mirror it as well
            if (getattr(m, "home_goals", None) is not None) and (
                getattr(m, "away_goals", None) is not None
            ):
                score = match_node.get("score") or {}
                if (
                    score.get("home") != m.home_goals
                    or score.get("away") != m.away_goals
                ):
                    score["home"] = m.home_goals
                    score["away"] = m.away_goals
                    match_node["score"] = score
                    changed = True

            if changed:
                data["match"] = match_node
                if args.dry_run:
                    logger.info(
                        "[dry-run] Would update match_id=%s with %s",
                        match_id,
                        {
                            "status": match_node.get("status"),
                            "home_goals": match_node.get("home_goals"),
                            "away_goals": match_node.get("away_goals"),
                        },
                    )
                else:
                    repo.match_predictions.update_one(
                        {"match_id": match_id}, {"$set": {"data": data}}
                    )
                    updated += 1
                    logger.info("Updated match_id=%s in match_predictions", match_id)

    logger.info(
        "Update complete: total_checked=%s, updated=%s, not_found=%s",
        total_checked,
        updated,
        not_found,
    )


if __name__ == "__main__":
    asyncio.run(main())
