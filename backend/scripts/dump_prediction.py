#!/usr/bin/env python3
"""
Dump a prediction document for inspection by match_id.

Usage:
  python3 backend/scripts/dump_prediction.py espn_746962
"""
import json
import os
import sys

sys.path.append(os.getcwd())

from src.dependencies import get_persistence_repository


def main():
    match_id = sys.argv[1] if len(sys.argv) > 1 else "espn_746962"
    repo = get_persistence_repository()
    doc = repo.match_predictions.find_one({"match_id": match_id})
    if not doc:
        print(f"No document found for match_id={match_id}")
        return
    # Pretty print limited fields
    out = {
        "match_id": doc.get("match_id"),
        "league_id": doc.get("league_id"),
        "data_match_keys": list(doc.get("data", {}).get("match", {}).keys()),
        "data_match": doc.get("data", {}).get("match", {}),
    }
    print(json.dumps(out, default=str, indent=2))


if __name__ == "__main__":
    main()
