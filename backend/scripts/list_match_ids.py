#!/usr/bin/env python3
"""
List match_id values from match_predictions collection (first N)
"""
import os
import sys

sys.path.append(os.getcwd())

from src.dependencies import get_persistence_repository


def main(limit=50):
    repo = get_persistence_repository()
    cursor = repo.match_predictions.find({}, {"match_id": 1}).limit(limit)
    for doc in cursor:
        print(doc.get("match_id"))


if __name__ == "__main__":
    main()
