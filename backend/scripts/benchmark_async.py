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
from typing import Any, List, Tuple

import httpx

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


@dataclass
class Result:
    durations: List[float]
    statuses: List[int]


class _FakeCollection:
    """Collection wrapper backed by an in-memory dict."""

    def __init__(self, storage: dict):
        self._storage = storage

    def find_one(self, filter=None, *a, **k):
        if not filter:
            return None
        if "match_id" in filter:
            return self._storage.get(filter.get("match_id"))
        if "key" in filter:
            return self._storage.get(filter.get("key"))
        return None

    def find(self, filter=None, *a, **k):
        if filter and "match_id" in filter:
            match_filter = filter.get("match_id")
            if isinstance(match_filter, dict) and "$in" in match_filter:
                ids = set(match_filter["$in"]) if match_filter["$in"] else set()
                return [doc for key, doc in self._storage.items() if key in ids]
        return list(self._storage.values())

    def update_one(self, filter, update, upsert=False):
        del upsert
        key = filter.get("match_id") or filter.get("key")
        set_doc = update.get("$set", {}) if isinstance(update, dict) else {}
        if key is not None:
            existing = self._storage.get(key, {})
            self._storage[key] = {**existing, **set_doc}
        return None

    def delete_many(self, filter=None):
        if not filter:
            deleted = len(self._storage)
            self._storage.clear()
            return deleted

        league_filter = filter.get("league_id") if filter else None
        if isinstance(league_filter, dict) and "$in" in league_filter:
            ids = set(league_filter["$in"]) if league_filter["$in"] else set()
            keys = [
                key
                for key, value in self._storage.items()
                if value.get("league_id") in ids
            ]
            for key in keys:
                del self._storage[key]
            return len(keys)

        return 0


class _FakeRepo:
    """Minimal in-memory repository used by the benchmark endpoints."""

    def __init__(self):
        self._app_state: dict[str, dict] = {}
        self._training_results: dict[str, dict] = {}
        self._match_predictions: dict[str, dict] = {}
        self._api_cache: dict[str, dict] = {}

        self.match_predictions = _FakeCollection(self._match_predictions)
        self.api_cache = _FakeCollection(self._api_cache)
        self.training_results = _FakeCollection(self._training_results)
        self.app_state = _FakeCollection(self._app_state)
        self.binary_artifacts = _FakeCollection({})

    def get_app_state(self, key):
        return self._app_state.get(key)

    def save_app_state(self, key, data):
        self._app_state[key] = data

    def get_cached_response(self, endpoint, params=None):
        cache_key = f"{endpoint}:{str(params)}"
        entry = self._api_cache.get(cache_key)
        if not entry:
            return None
        return entry.get("data")

    def save_cached_response(self, endpoint, data, params=None, ttl_seconds=3600):
        del ttl_seconds
        cache_key = f"{endpoint}:{str(params)}"
        self._api_cache[cache_key] = {"data": data, "expires_at": None}

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

    def get_match_prediction(self, match_id):
        doc = self._match_predictions.get(match_id)
        if not doc:
            return None
        return doc.get("data")

    def get_match_predictions_bulk(self, match_ids):
        return {
            match_id: (self._match_predictions.get(match_id) or {}).get("data")
            for match_id in match_ids
        }

    def save_match_prediction(self, match_id, league_id, data, ttl_seconds=86400):
        del ttl_seconds
        self._match_predictions[match_id] = {
            "data": data,
            "league_id": league_id,
            "expires_at": None,
            "last_updated": time.time(),
        }

    def bulk_save_predictions(self, batch):
        for prediction in batch:
            match_id = prediction.get("match_id")
            if not match_id:
                continue
            self._match_predictions[match_id] = {
                "data": prediction.get("data"),
                "league_id": prediction.get("league_id"),
                "expires_at": None,
                "last_updated": time.time(),
            }
        return None


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


def _load_app() -> Any:
    """Import the FastAPI app in-process for benchmarking."""
    try:
        from src.api.main import app  # type: ignore
    except Exception as exc:  # pragma: no cover - runtime dependent
        print("Failed to import app:", exc)
        raise
    return app


def _patch_repository_consumers(importlib_module: Any, fake_repo: _FakeRepo) -> None:
    patch_targets = (
        "src.api.services.data_loader",
        "src.api.routers.matches",
        "src.api.routers.predictions",
        "src.worker",
    )

    for module_name in patch_targets:
        try:
            module = importlib_module.import_module(module_name)
            if hasattr(module, "get_mongo_repository"):
                setattr(module, "get_mongo_repository", lambda: fake_repo)
        except Exception:
            continue


def _install_fake_repository() -> None:
    """Install an in-memory repository so local benchmarks do not require MongoDB."""
    try:
        import importlib

        mongo_mod = importlib.import_module(
            "src.infrastructure.repositories.mongo_repository"
        )
        deps_mod = importlib.import_module("src.dependencies")

        fake_repo = _FakeRepo()
        if hasattr(deps_mod, "get_persistence_repository"):
            deps_mod.get_persistence_repository = lambda: fake_repo

        mongo_mod.get_mongo_repository = lambda: fake_repo
        _patch_repository_consumers(importlib, fake_repo)
    except Exception:
        pass


def _run_endpoint_benchmarks(
    app: Any, endpoints: List[str], requests: int, concurrency: int
) -> dict:
    loop = asyncio.get_event_loop()
    overall = {}

    for endpoint in endpoints:
        print(
            f"Running benchmark: {endpoint} "
            f"(requests={requests}, concurrency={concurrency})"
        )
        res = loop.run_until_complete(
            run_benchmark(app, endpoint, "GET", requests, concurrency)
        )
        summary = summarize(res)
        overall[endpoint] = summary
        print(json.dumps({"endpoint": endpoint, "summary": summary}, indent=2))

        file_name = os.path.join(
            ensure_tmp_dir(), f"benchmark_{endpoint.strip('/').replace('/', '_')}.json"
        )
        with open(file_name, "w") as fh:
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

    return overall


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--requests", type=int, default=50)
    parser.add_argument("-c", "--concurrency", type=int, default=10)
    parser.add_argument("--endpoints", nargs="*", default=None)
    args = parser.parse_args()

    app = _load_app()

    endpoints = args.endpoints or [
        "/api/v1/suggested-picks/match/m_1001",
        "/api/v1/predictions/league/E0",
        "/api/v1/predictions/match/m_1001",
    ]

    ensure_tmp_dir()
    _install_fake_repository()
    _run_endpoint_benchmarks(app, endpoints, args.requests, args.concurrency)


if __name__ == "__main__":
    main()
