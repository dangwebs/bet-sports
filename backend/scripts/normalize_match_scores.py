#!/usr/bin/env python3
"""Normaliza campos de score en `match_predictions`.

Convierte valores numéricos almacenados como strings a enteros en los campos
`home_goals`, `away_goals`, `home_score`, `away_score` y en `score`.

Soporta `--dry-run` para mostrar los cambios propuestos sin aplicar.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Tuple

from pymongo import MongoClient


def parse_int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
        try:
            return int(v)
        except Exception:
            try:
                return int(float(v))
            except Exception:
                return None
    return None


def normalize_match(  # noqa: C901
    m: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    new_m = dict(m)
    # Coerce common scalar fields
    for k in ("home_goals", "away_goals", "home_score", "away_score"):
        if k in m:
            val = parse_int(m.get(k))
            if val is not None and m.get(k) != val:
                new_m[k] = val
                changed = True

    # Handle `score` which may be dict or string like "2-1"
    s = m.get("score")
    if isinstance(s, dict):
        h = parse_int(s.get("home") or s.get("home_goals") or s.get("home_score"))
        a = parse_int(s.get("away") or s.get("away_goals") or s.get("away_score"))
        if (h is not None and s.get("home") != h) or (
            a is not None and s.get("away") != a
        ):
            new_s = dict(s)
            if h is not None:
                new_s["home"] = h
            if a is not None:
                new_s["away"] = a
            new_m["score"] = new_s
            changed = True
    elif isinstance(s, str):
        parts = s.split("-")
        if len(parts) >= 2:
            h = parse_int(parts[0])
            a = parse_int(parts[1])
            if h is not None and a is not None:
                # write canonical fields
                new_m["home_goals"] = h
                new_m["away_goals"] = a
                changed = True

    return changed, new_m


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true", help="No aplicar cambios, solo mostrar"
    )
    parser.add_argument(
        "--limit", type=int, default=1000, help="Límite de documentos a comprobar"
    )
    args = parser.parse_args()

    uri = (
        os.environ.get("MONGO_URI")
        or os.environ.get("MONGODB_URI")
        or "mongodb://mongodb:27017"
    )
    dbname = os.environ.get("MONGO_DB_NAME", "bjj_betsports")
    client = MongoClient(uri)
    db = client[dbname]
    coll = db["match_predictions"]

    # Buscar documentos donde scores están como strings (o score.home/away como strings)
    query = {
        "$or": [
            {"data.match.home_score": {"$type": 2}},
            {"data.match.away_score": {"$type": 2}},
            {"data.match.home_goals": {"$type": 2}},
            {"data.match.away_goals": {"$type": 2}},
            {"data.match.score": {"$type": 2}},
            {"data.match.score.home": {"$type": 2}},
            {"data.match.score.away": {"$type": 2}},
        ]
    }

    cursor = coll.find(query).limit(args.limit)
    to_update = []
    checked = 0
    for d in cursor:
        checked += 1
        m = d.get("data", {}).get("match", {})
        changed, new_m = normalize_match(m)
        if changed:
            to_update.append(
                {"_id": d.get("_id"), "match_id": d.get("match_id"), "new_match": new_m}
            )

    print(
        f"Found {len(to_update)} documents to update "
        f"(checked {checked}, limit {args.limit})."
    )
    if args.dry_run:
        print(json.dumps(to_update, default=str, indent=2, ensure_ascii=False))
        return

    applied = 0
    for item in to_update:
        _id = item["_id"]
        new_match = item["new_match"]
        coll.update_one({"_id": _id}, {"$set": {"data.match": new_match}})
        applied += 1

    print(f"Applied {applied} updates.")


if __name__ == "__main__":
    main()
