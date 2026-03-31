#!/usr/bin/env python3
"""
Inspect mapping between external finished matches and match_predictions documents.

Usage:
  python3 backend/scripts/inspect_match_mapping.py --league D1 --days-back 30 --limit 10

This script prints for each finished match the `match.id`, candidate IDs tried
and whether a document in `match_predictions` was found for any candidate.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from src.dependencies import get_match_aggregator_service, get_persistence_repository


async def gather_finished_matches(aggregator, league_id: str, days_back: int):
    now = datetime.utcnow()
    date_to = now.strftime("%Y-%m-%d")
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

    matches = []
    try:
        if aggregator.football_data_org.is_configured:
            fd_matches = await aggregator.football_data_org.get_finished_matches(
                date_from=date_from, date_to=date_to, league_codes=[league_id]
            )
            matches.extend(fd_matches or [])
    except Exception as e:
        print(f"[inspect] Football-Data.org fetch failed for {league_id}: {e}")

    try:
        espn_matches = await aggregator.espn.get_finished_matches(
            league_codes=[league_id], days_back=days_back
        )
        matches.extend(espn_matches or [])
    except Exception as e:
        print(f"[inspect] ESPN fetch failed for {league_id}: {e}")

    try:
        ts_matches = await aggregator.thesportsdb.get_past_events(
            league_id, max_events=200
        )
        matches.extend(ts_matches or [])
    except Exception as e:
        print(f"[inspect] TheSportsDB fetch failed for {league_id}: {e}")

    unique = {}
    for m in matches:
        if not m or not getattr(m, "id", None):
            continue
        unique[str(m.id)] = m

    return list(unique.values())


async def main():
    parser = argparse.ArgumentParser(
        description="Inspect finished-match -> prediction mapping"
    )
    parser.add_argument(
        "--league", type=str, default="D1", help="League id to inspect (e.g. D1)"
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=30,
        help="Days to look back for finished matches",
    )
    parser.add_argument("--limit", type=int, default=10, help="Max matches to inspect")
    args = parser.parse_args()

    aggregator = get_match_aggregator_service()
    repo = get_persistence_repository()

    matches = await gather_finished_matches(aggregator, args.league, args.days_back)
    print(
        f"[inspect] Found {len(matches)} finished matches "
        f"for league {args.league} (looking back {args.days_back} days)"
    )

    checked = 0
    for m in matches:
        if checked >= args.limit:
            break
        mid = getattr(m, "id", None)
        status = getattr(m, "status", None)
        hg = getattr(m, "home_goals", None)
        ag = getattr(m, "away_goals", None)

        print("----")
        print(f"match.id={mid}  status={status}  home_goals={hg}  away_goals={ag}")

        mid_str = str(mid)
        candidate_ids = [mid_str]
        if mid_str.isdigit():
            candidate_ids.append(f"espn_{mid_str}")
        if mid_str.startswith("espn_"):
            candidate_ids.append(mid_str.split("espn_")[-1])
        candidate_ids.append(mid_str.replace(" ", "").replace("-", "_"))

        print("candidate_ids_tried=", candidate_ids)

        found_any = False
        for cid in candidate_ids:
            try:
                doc = repo.match_predictions.find_one({"match_id": cid})
            except Exception as e:
                print(f"repo lookup error for {cid}: {e}")
                doc = None

            if doc:
                found_any = True
                print(f"FOUND -> doc.match_id={doc.get('match_id')} (candidate={cid})")
                data = doc.get("data", {}) or {}
                match_node = data.get("match", {}) or {}
                print(
                    f"  doc.data.match.status={match_node.get('status')} "
                    f"home_goals={match_node.get('home_goals')} "
                    f"away_goals={match_node.get('away_goals')}"
                )
                break
            else:
                print(f"  not found for candidate: {cid}")

        if not found_any:
            print(f"NO match_predictions doc found for external match.id={mid}")

        checked += 1

    print("[inspect] finished")


if __name__ == "__main__":
    asyncio.run(main())
