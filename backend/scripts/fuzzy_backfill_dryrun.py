#!/usr/bin/env python3
"""
Dry-run fuzzy backfill: try to map external finished matches to stored
`match_predictions` documents using date windows and team-name matching.

This script supports configurable thresholds and uses a small canonical
team alias map to improve matching across provider name variants.

Usage:
  python3 backend/scripts/fuzzy_backfill_dryrun.py \
    --league D1 --days-back 30 --limit 50 --dry-run
"""

import argparse
import asyncio
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

sys.path.append(os.getcwd())

from src.dependencies import get_match_aggregator_service, get_persistence_repository
from src.infrastructure.data.team_aliases import canonical_team_key


def normalize_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def normalize_tokens(s: str):
    """Return a list of meaningful tokens from a team name for fuzzy matching."""
    if not s:
        return []
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode()
    s = s.lower()
    # Replace punctuation with spaces, split into tokens
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = [t for t in s.split() if t]
    # Remove common noisy tokens — keep 'united'/'city' to preserve distinctions
    stop = {"fc", "cf", "afc", "ac", "sc", "club", "team", "a", "the", "de", "la", "el"}
    return [t for t in tokens if t not in stop]


def seq_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def to_utc(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        # Try ISO
        try:
            return datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
        except Exception:
            try:
                return datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            except Exception:
                return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None


async def gather_finished_matches(aggregator, league_id: str, days_back: int):
    now = datetime.utcnow()
    date_to = now.strftime("%Y-%m-%d")
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

    matches = []

    # Football-Data.org
    try:
        if aggregator.football_data_org.is_configured:
            fd_matches = await aggregator.football_data_org.get_finished_matches(
                date_from=date_from, date_to=date_to, league_codes=[league_id]
            )
            matches.extend(fd_matches or [])
    except Exception as e:
        print(f"[fuzzy] Football-Data fetch failed: {e}")

    # ESPN
    try:
        espn_matches = await aggregator.espn.get_finished_matches(
            league_codes=[league_id], days_back=days_back
        )
        matches.extend(espn_matches or [])
    except Exception as e:
        print(f"[fuzzy] ESPN fetch failed: {e}")

    # TheSportsDB
    try:
        ts_matches = await aggregator.thesportsdb.get_past_events(
            league_id, max_events=200
        )
        matches.extend(ts_matches or [])
    except Exception as e:
        print(f"[fuzzy] TheSportsDB fetch failed: {e}")

    # Deduplicate by id
    unique = {}
    for m in matches:
        if not m or not getattr(m, "id", None):
            continue
        unique[str(m.id)] = m
    return list(unique.values())


async def main():  # noqa: C901
    parser = argparse.ArgumentParser(description="Fuzzy backfill dry-run")
    parser.add_argument("--league", type=str, required=True)
    parser.add_argument("--days-back", type=int, default=30)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--threshold", type=int, default=4, help="Score threshold to accept fuzzy match"
    )
    parser.add_argument(
        "--max-date-hours",
        type=int,
        default=48,
        help="Maximum allowed date difference in hours for candidate matches",
    )
    parser.add_argument(
        "--date-bonus-hours",
        type=int,
        default=12,
        help="Hours window for larger date bonus",
    )
    parser.add_argument(
        "--date-bonus2-hours",
        type=int,
        default=24,
        help="Hours window for smaller date bonus",
    )
    args = parser.parse_args()

    aggregator = get_match_aggregator_service()
    repo = get_persistence_repository()

    matches = await gather_finished_matches(aggregator, args.league, args.days_back)
    print(f"[fuzzy] Found {len(matches)} finished matches for league {args.league}")

    checked = 0
    matched_by_id = 0
    matched_by_fuzzy = 0
    not_found = 0

    # precompute date thresholds from args
    max_date_seconds = args.max_date_hours * 60 * 60
    date_bonus_small = args.date_bonus_hours * 60 * 60
    date_bonus_large = args.date_bonus2_hours * 60 * 60

    for m in matches:
        if checked >= args.limit:
            break
        checked += 1
        mid = str(getattr(m, "id", ""))
        status = getattr(m, "status", None)
        m_date = to_utc(getattr(m, "match_date", None))
        home_name = (
            getattr(getattr(m, "home_team", None), "name", None)
            or getattr(m, "home_team", None)
            or getattr(m, "home_name", None)
        )
        away_name = (
            getattr(getattr(m, "away_team", None), "name", None)
            or getattr(m, "away_team", None)
            or getattr(m, "away_name", None)
        )

        print("----")
        print(
            f"ext.id={mid}  date={m_date}  status={status}  "
            f"home={home_name}  away={away_name}"
        )

        # candidate ids
        candidates = [mid]
        if mid.isdigit():
            candidates.append(f"espn_{mid}")
        if mid.startswith("espn_"):
            candidates.append(mid.split("espn_")[-1])
        candidates.append(mid.replace(" ", "").replace("-", "_"))

        found = None
        for cid in candidates:
            doc = repo.match_predictions.find_one({"match_id": cid})
            if doc:
                found = ("id", cid, doc)
                break

        if found:
            matched_by_id += 1
            print(
                f"FOUND by id -> candidate={found[1]} "
                f"doc_match_id={found[2].get('match_id')}"
            )
            continue

        # Fuzzy: scan match_predictions in same league and compare date + team names
        cursor = repo.match_predictions.find({"league_id": args.league})
        best = None
        best_score = 0

        for doc in cursor:
            doc_match = (doc.get("data") or {}).get("match") or {}
            doc_date = to_utc(doc_match.get("match_date"))
            if not doc_date or not m_date:
                continue
            delta = abs((doc_date - m_date).total_seconds())
            if delta > max_date_seconds:
                continue

            # extract doc team names
            def extract_team_name(d, side):
                keys = [f"{side}_team", f"{side}_name", f"{side}Team", side]
                for k in keys:
                    v = doc_match.get(k)
                    if isinstance(v, dict) and v.get("name"):
                        return v.get("name")
                    if isinstance(v, str) and v:
                        return v
                if doc_match.get("home_team") and isinstance(
                    doc_match.get("home_team"), dict
                ):
                    return (
                        doc_match.get("home_team").get("name")
                        if side == "home"
                        else doc_match.get("away_team").get("name")
                    )
                return None

            doc_home = extract_team_name(doc_match, "home")
            doc_away = extract_team_name(doc_match, "away")

            ext_home_raw = home_name or ""
            ext_away_raw = away_name or ""

            # basic normalized tokens
            tokens_ext_home = set(normalize_tokens(ext_home_raw))
            tokens_ext_away = set(normalize_tokens(ext_away_raw))
            tokens_doc_home = set(normalize_tokens(doc_home or ""))
            tokens_doc_away = set(normalize_tokens(doc_away or ""))

            # sequence similarity on raw names
            seq_home = seq_ratio(ext_home_raw or "", doc_home or "")
            seq_away = seq_ratio(ext_away_raw or "", doc_away or "")

            # jaccard/token overlap
            def jaccard(a, b):
                if not a and not b:
                    return 0.0
                set_a = set(a)
                set_b = set(b)
                if not set_a or not set_b:
                    return 0.0
                return float(len(set_a & set_b)) / float(len(set_a | set_b))

            j_home = jaccard(tokens_ext_home, tokens_doc_home)
            j_away = jaccard(tokens_ext_away, tokens_doc_away)

            # canonical keys
            canon_ext_home = canonical_team_key(ext_home_raw)
            canon_ext_away = canonical_team_key(ext_away_raw)
            canon_doc_home = canonical_team_key(doc_home or "")
            canon_doc_away = canonical_team_key(doc_away or "")

            tokens_canon_ext_home = (
                set(canon_ext_home.split("_")) if canon_ext_home else set()
            )
            tokens_canon_doc_home = (
                set(canon_doc_home.split("_")) if canon_doc_home else set()
            )
            tokens_canon_ext_away = (
                set(canon_ext_away.split("_")) if canon_ext_away else set()
            )
            tokens_canon_doc_away = (
                set(canon_doc_away.split("_")) if canon_doc_away else set()
            )

            # scoring
            score = 0

            # canonical strong match
            if canon_ext_home and canon_doc_home and canon_ext_home == canon_doc_home:
                score += 6
            if canon_ext_away and canon_doc_away and canon_ext_away == canon_doc_away:
                score += 6

            # canonical token jaccard / sequence
            j_can_home = jaccard(tokens_canon_ext_home, tokens_canon_doc_home)
            j_can_away = jaccard(tokens_canon_ext_away, tokens_canon_doc_away)

            if j_can_home >= 0.5 or seq_home >= 0.85:
                score += 3
            elif j_can_home >= 0.3 or seq_home >= 0.6:
                score += 1

            if j_can_away >= 0.5 or seq_away >= 0.85:
                score += 3
            elif j_can_away >= 0.3 or seq_away >= 0.6:
                score += 1

            # swapped weaker signals
            j_home_swap = jaccard(tokens_ext_home, tokens_doc_away)
            j_away_swap = jaccard(tokens_ext_away, tokens_doc_home)
            if (
                j_home_swap >= 0.5
                or seq_ratio(ext_home_raw or "", doc_away or "") >= 0.8
            ):
                score += 1
            if (
                j_away_swap >= 0.5
                or seq_ratio(ext_away_raw or "", doc_home or "") >= 0.8
            ):
                score += 1

            # date proximity bonus
            if delta <= date_bonus_small:
                score += 2
            elif delta <= date_bonus_large:
                score += 1

            if score > best_score:
                best_score = score
                best = (
                    doc,
                    doc_match,
                    doc_home,
                    doc_away,
                    delta,
                    j_home,
                    j_away,
                    seq_home,
                    seq_away,
                )

        threshold = args.threshold
        if best and best_score >= threshold:
            matched_by_fuzzy += 1
            doc = best[0]
            doc_match = best[1]
            delta_sec = int(best[4])
            j_home = best[5]
            j_away = best[6]
            seq_home = best[7]
            seq_away = best[8]
            print(
                f"FOUND by fuzzy -> doc.match_id={doc.get('match_id')} "
                f"date_delta_sec={delta_sec} score={best_score}"
            )
            print(f"  doc_home={best[2]} doc_away={best[3]}")
            print(
                f"  metrics: j_home={j_home:.2f} j_away={j_away:.2f} "
                f"seq_home={seq_home:.2f} seq_away={seq_away:.2f}"
            )
            # Show proposed update
            print(
                f"  proposed: status={status} "
                f"home_goals={getattr(m, 'home_goals', None)} "
                f"away_goals={getattr(m, 'away_goals', None)}"
            )
            # Do not write in dry-run
            if not args.dry_run:
                data = doc.get("data") or {}
                match_node = data.get("match") or {}
                if getattr(m, "status", None):
                    match_node["status"] = getattr(m, "status")
                if getattr(m, "home_goals", None) is not None:
                    match_node["home_goals"] = getattr(m, "home_goals")
                if getattr(m, "away_goals", None) is not None:
                    match_node["away_goals"] = getattr(m, "away_goals")
                data["match"] = match_node
                repo.match_predictions.update_one(
                    {"match_id": doc.get("match_id")}, {"$set": {"data": data}}
                )
                print(f"  Applied update to {doc.get('match_id')}")
            continue

        not_found += 1
        print(
            f"NO match_predictions doc found for external "
            f"id={mid} (candidates tried: {candidates})"
        )

    print("[fuzzy] Summary:")
    print(
        f"  checked={checked}  matched_by_id={matched_by_id}  "
        f"matched_by_fuzzy={matched_by_fuzzy}  not_found={not_found}"
    )


if __name__ == "__main__":
    asyncio.run(main())
