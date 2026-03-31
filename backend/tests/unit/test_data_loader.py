from datetime import datetime

from src.api.services.data_loader import DataLoader


class FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query=None):
        return iter(self._docs)

    def find_one(self, query):
        for d in self._docs:
            if d.get("match_id") == query.get("match_id"):
                return d
        return None


class FakeRepo:
    def __init__(self, docs, training=None, updated_at=None):
        self.match_predictions = FakeCollection(docs)
        self._training = training
        self._updated_at = updated_at

    def get_training_result_with_timestamp(self, key):
        return self._training, self._updated_at


def test_data_loader_loads_predictions_and_training_result():
    doc = {
        "league_id": "E0",
        "match_id": "m1",
        "prediction": {
            "match": {
                "id": "m1",
                "match_date": "2026-03-31T12:00:00Z",
                "home_team": {"id": "h1", "name": "A"},
                "away_team": {"id": "a1", "name": "B"},
                "status": "scheduled",
            },
            "prediction": {"match_id": "m1", "home_win_probability": 0.5},
        },
    }

    training = {"version": "v1"}
    updated_at = datetime(2026, 3, 31)
    repo = FakeRepo([doc], training=training, updated_at=updated_at)
    loader = DataLoader(repository=repo)

    preds = loader.load_predictions_for_league("E0")
    assert isinstance(preds, list)
    assert len(preds) == 1

    result, ts = loader.get_latest_training_result()
    assert result == training
    assert ts is not None
