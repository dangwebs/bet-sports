from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend package is importable when running tests from repo root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from src.api.main import app  # noqa: E402

client = TestClient(app)


def test_health_check() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_get_leagues() -> None:
    r = client.get("/api/v1/leagues")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("countries"), list)
    assert isinstance(body.get("total_leagues"), int)
