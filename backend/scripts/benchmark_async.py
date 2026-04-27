#!/usr/bin/env python3
"""Benchmark endpoints in-process using httpx AsyncClient(app=app).

Usage:
  python scripts/benchmark_async.py -n 100 -c 10

The script imports `src.api.main:app` and runs concurrent requests against
the provided endpoints. Results are printed and saved to `backend/tmp/`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics

# Make sure the project root (backend/) is on sys.path so `from src...` works
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import httpx

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


@dataclass
class Result:
    durations: List[float]
    statuses: List[int]


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    d0 = s[f] * (c - k) + s[c] * (k - f)
    return d0


async def make_request(
    client: httpx.AsyncClient, method: str, url: str, sem: asyncio.Semaphore
) -> Tuple[float, int]:
    async with sem:
        start = time.perf_counter()
        try:
            resp = await client.request(method, url)
            elapsed = (time.perf_counter() - start) * 1000.0
            return elapsed, resp.status_code
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000.0
            return elapsed, 0


async def run_benchmark(
    app, path: str, method: str = "GET", total: int = 100, concurrency: int = 10
) -> Result:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        tasks = [make_request(client, method, path, sem) for _ in range(total)]
        results = await asyncio.gather(*tasks)

    durations = [r[0] for r in results]
    statuses = [r[1] for r in results]
    return Result(durations=durations, statuses=statuses)


def summarize(res: Result) -> dict:
    d = res.durations
    ok = sum(1 for s in res.statuses if 200 <= s < 300)
    return {
        "count": len(d),
        "ok": ok,
        "errors": len(d) - ok,
        "min_ms": min(d) if d else 0,
        "p50_ms": percentile(d, 50),
        "p95_ms": percentile(d, 95),
        "max_ms": max(d) if d else 0,
        "mean_ms": statistics.mean(d) if d else 0,
    }


def ensure_tmp_dir():
    path = os.path.join(os.path.dirname(__file__), "..", "tmp")
    path = os.path.normpath(path)
    os.makedirs(path, exist_ok=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--requests", type=int, default=50)
    parser.add_argument("-c", "--concurrency", type=int, default=10)
    parser.add_argument("--endpoints", nargs="*", default=None)
    args = parser.parse_args()

    # Import the FastAPI app in-process
    try:
        from src.api.main import app  # type: ignore
    except Exception as exc:  # pragma: no cover - runtime dependent
        print("Failed to import app:", exc)
        raise

    # Default endpoints to exercise
    endpoints = args.endpoints or [
        "/api/v1/suggested-picks/match/m_1001",
        "/api/v1/predictions/league/E0",
        "/api/v1/predictions/match/m_1001",
    ]

    ensure_tmp_dir()
    loop = asyncio.get_event_loop()
    overall = {}
    # Install in-memory fakes to avoid requiring a running MongoDB for local benchmarking
    try:
        # Lightweight fake repository with minimal methods used by endpoints
        import importlib

        mongo_mod = importlib.import_module(
            "src.infrastructure.repositories.mongo_repository"
        )
        deps_mod = importlib.import_module("src.dependencies")
        preds_mod = importlib.import_module("src.api.routers.predictions")

        class _FakeCollection:
            """Lightweight collection wrapper backed by an in-memory dict.

            Supports `find_one`, `find`, `update_one`, and `delete_many` with
            the minimal semantics required by the application routers.
            """

            def __init__(self, storage: dict):
                self._storage = storage

            def find_one(self, filter=None, *a, **k):
                if not filter:
                    return None
                # match by match_id or key
                if "match_id" in filter:
                    mid = filter.get("match_id")
                    # simple equality
                    return self._storage.get(mid)
                if "key" in filter:
                    return self._storage.get(filter.get("key"))
                return None

            def find(self, filter=None, *a, **k):
                # support queries like {"match_id": {"$in": [...]}}
                if filter and "match_id" in filter:
                    mid = filter.get("match_id")
                    if isinstance(mid, dict) and "$in" in mid:
                        ids = set(mid["$in"]) if mid["$in"] else set()
                        return [doc for k, doc in self._storage.items() if k in ids]
                # default: return all stored docs
                return list(self._storage.values())

            def update_one(self, filter, update, upsert=False):
                key = filter.get("match_id") or filter.get("key")
                set_doc = update.get("$set", {}) if isinstance(update, dict) else {}
                if key is not None:
                    existing = self._storage.get(key, {})
                    # shallow merge set_doc into existing
                    merged = {**existing, **set_doc}
                    self._storage[key] = merged
                return None

            def delete_many(self, filter=None):
                if not filter:
                    deleted = len(self._storage)
                    self._storage.clear()
                    return deleted
                # support delete by league_id list
                if (
                    "league_id" in filter
                    and isinstance(filter.get("league_id"), dict)
                    and "$in" in filter["league_id"]
                ):
                    ids = (
                        set(filter["league_id"]["$in"])
                        if filter["league_id"]["$in"]
                        else set()
                    )
                    keys = [
                        k for k, v in self._storage.items() if v.get("league_id") in ids
                    ]
                    for k in keys:
                        del self._storage[k]
                    return len(keys)
                return 0

        class _FakeRepo:
            """Minimal in-memory fake repository implementing the methods
            exercised by the application during benchmarking.

            It is intentionally simple: stores data in dicts and returns
            sensible defaults. Not meant to be a fidelity replacement
            for Mongo, only to allow local benchmarking without a DB.
            """

            def __init__(self):
                self._app_state: dict[str, dict] = {}
                self._training_results: dict[str, dict] = {}
                self._match_predictions: dict[str, dict] = {}
                self._api_cache: dict[str, dict] = {}

                # Expose collection-like attributes for consumers that access
                # `repository.match_predictions.find_one(...)` directly.
                self.match_predictions = _FakeCollection(self._match_predictions)
                self.api_cache = _FakeCollection(self._api_cache)
                self.training_results = _FakeCollection(self._training_results)
                self.app_state = _FakeCollection(self._app_state)
                self.binary_artifacts = _FakeCollection({})

            # --- App state ---
            def get_app_state(self, key):
                return self._app_state.get(key)

            def save_app_state(self, key, data):
                self._app_state[key] = data

            # --- API cache ---
            def get_cached_response(self, endpoint, params=None):
                k = f"{endpoint}:{str(params)}"
                entry = self._api_cache.get(k)
                if not entry:
                    return None
                return entry.get("data")

            def save_cached_response(
                self, endpoint, data, params=None, ttl_seconds=3600
            ):
                k = f"{endpoint}:{str(params)}"
                self._api_cache[k] = {"data": data, "expires_at": None}

            # --- Training results ---
            def get_training_result_with_timestamp(self, key):
                doc = self._training_results.get(key)
                if not doc:
                    return None, None
                return doc.get("data"), doc.get("last_updated")

            def save_training_result(self, key, data):
                self._training_results[key] = {
                    "data": data,
                    "last_updated": time.time(),
                }

            # --- Match predictions ---
            def get_match_prediction(self, match_id):
                doc = self._match_predictions.get(match_id)
                if not doc:
                    return None
                return doc.get("data")

            def get_match_predictions_bulk(self, match_ids):
                return {
                    m: (self._match_predictions.get(m) or {}).get("data")
                    for m in match_ids
                }

            def save_match_prediction(
                self, match_id, league_id, data, ttl_seconds=86400
            ):
                self._match_predictions[match_id] = {
                    "data": data,
                    "league_id": league_id,
                    "expires_at": None,
                    "last_updated": time.time(),
                }

            def bulk_save_predictions(self, batch):
                for p in batch:
                    mid = p.get("match_id")
                    if not mid:
                        continue
                    self._match_predictions[mid] = {
                        "data": p.get("data"),
                        "league_id": p.get("league_id"),
                        "expires_at": None,
                        "last_updated": time.time(),
                    }
                return None

        fake_repo = _FakeRepo()

        # Monkeypatch dependency factories to return fake repo where possible
        if hasattr(deps_mod, "get_persistence_repository"):
            deps_mod.get_persistence_repository = lambda: fake_repo
        # Patch the canonical mongo factory in the repo module
        mongo_mod.get_mongo_repository = lambda: fake_repo
        # Some modules import get_mongo_repository at module level; patch common consumers
        for m in (
            "src.api.services.data_loader",
            "src.api.routers.matches",
            "src.api.routers.predictions",
            "src.worker",
        ):
            try:
                mod = importlib.import_module(m)
                if hasattr(mod, "get_mongo_repository"):
                    setattr(mod, "get_mongo_repository", lambda: fake_repo)
            except Exception:
                continue
    except Exception:
        # If monkeypatching fails, continue — requests may hit real DB and fail.
        pass
    for ep in endpoints:
        print(
            f"Running benchmark: {ep} (requests={args.requests}, concurrency={args.concurrency})"
        )
        res = loop.run_until_complete(
            run_benchmark(app, ep, "GET", args.requests, args.concurrency)
        )
        summary = summarize(res)
        overall[ep] = summary
        print(json.dumps({"endpoint": ep, "summary": summary}, indent=2))

        # Save raw durations
        fname = os.path.join(
            ensure_tmp_dir(), f"benchmark_{ep.strip('/').replace('/', '_')}.json"
        )
        with open(fname, "w") as fh:
            json.dump(
                {
                    "durations_ms": res.durations,
                    "statuses": res.statuses,
                    "summary": summary,
                },
                fh,
            )

    out_fname = os.path.join(ensure_tmp_dir(), "benchmark_summary.json")
    with open(out_fname, "w") as fh:
        json.dump(overall, fh, indent=2)
    print("Benchmark complete. Results saved to backend/tmp/")


if __name__ == "__main__":
    main()
