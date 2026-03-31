from datetime import timedelta
from types import SimpleNamespace

import pytest
from src.application.services.auto_labeler import AutoLabeler
from src.utils.time_utils import get_current_time


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.updates = []

    def find(self, query):
        # Return iterator to mimic pymongo cursor
        return iter(self.docs)

    def update_one(self, filter_q, update_q):
        self.updates.append((filter_q, update_q))


class FakeRepo:
    def __init__(self, docs):
        self.match_predictions = FakeCollection(docs)


class FakeFootballDataOrg:
    is_configured = True

    async def get_match_details(self, match_id):
        # Return a simple object with final score properties
        class M:
            status = "FT"
            home_goals = 2
            away_goals = 1
            home_corners = 5
            away_corners = 3
            home_yellow_cards = 2
            away_yellow_cards = 1

        return M()


@pytest.mark.asyncio
async def test_auto_labeler_labels_finished_matches():
    now = get_current_time()
    docs = [{"match_id": "m_test", "expires_at": now - timedelta(hours=1)}]
    repo = FakeRepo(docs)
    data_sources = SimpleNamespace(football_data_org=FakeFootballDataOrg())
    auto_labeler = AutoLabeler(repo, data_sources, cache_service=None)

    labeled = await auto_labeler.run(limit=10)
    assert labeled == 1
    assert len(repo.match_predictions.updates) == 1
    filter_q, update_q = repo.match_predictions.updates[0]
    assert filter_q.get("match_id") == "m_test"
    # Expect label set in the update
    assert "$set" in update_q
    payload = update_q["$set"]
    assert payload.get("labeled") is True
    assert payload.get("label")["home_goals"] == 2
    assert payload.get("label")["away_goals"] == 1
    assert payload.get("label")["home_corners"] == 5
    assert payload.get("label")["away_corners"] == 3
    assert payload.get("label_source") in ("football_data_org", "cache")
