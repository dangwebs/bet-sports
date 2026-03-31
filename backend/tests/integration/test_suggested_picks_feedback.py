import src.api.routers.picks as picks_module
from fastapi.testclient import TestClient
from src.api.main import app


class DummyLearningService:
    def __init__(self):
        self.registered = []

    def register_feedback(self, feedback):
        self.registered.append(feedback)

    def get_market_adjustment(self, market_type: str) -> float:
        return 0.88

    def get_all_stats(self):
        return {}


def test_feedback_endpoint_registers_and_returns_adjustment(monkeypatch):
    # Patch LearningService used inside the router
    picks_module.LearningService = DummyLearningService

    client = TestClient(app)

    payload = {
        "match_id": "m1",
        "market_type": "corners_over",
        "prediction": "over25",
        "actual_outcome": "over25",
        "was_correct": True,
        "odds": 2.5,
        "stake": 5.0,
    }

    r = client.post("/api/v1/suggested-picks/feedback", json=payload)

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["market_type"] == "corners_over"
    assert isinstance(data["new_confidence_adjustment"], float)
