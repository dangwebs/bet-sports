from src.application.services.labeler import reconcile_predictions


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query=None):
        # return list to emulate cursor
        return list(self.docs)

    def update_one(self, filter, update, upsert=False):
        # naive update implementation for tests
        for d in self.docs:
            if (
                filter.get("match_id") and d.get("match_id") == filter.get("match_id")
            ) or (filter.get("_id") and d.get("_id") == filter.get("_id")):
                # apply $set
                for k, v in update.get("$set", {}).items():
                    d[k] = v
                return
        if upsert:
            new = {**(update.get("$set", {}) or {}), **(filter or {})}
            self.docs.append(new)


class FakeAudit:
    def __init__(self):
        self.items = []

    def insert_one(self, doc):
        self.items.append(doc)


class FakeRepo:
    def __init__(self, docs):
        self.match_predictions = FakeCollection(docs)
        self.db = {"labeling_audit": FakeAudit()}


def test_labeler_dry_run_and_persist():
    docs = [
        {
            "_id": "1",
            "match_id": "m_1001",
            "data": {
                "match": {"status": "FT", "home_goals": 2, "away_goals": 1},
                "prediction": {"confidence": 0.75},
            },
        }
    ]

    repo = FakeRepo([d.copy() for d in docs])
    report = reconcile_predictions(repo, window_days=90, dry_run=True)
    assert report["labeled_count"] == 1
    # repo should not be modified
    assert not repo.match_predictions.docs[0].get("labeled")

    repo2 = FakeRepo([d.copy() for d in docs])
    report2 = reconcile_predictions(repo2, window_days=90, dry_run=False)
    assert report2["labeled_count"] == 1
    # repo2 should have been updated
    assert repo2.match_predictions.docs[0].get("labeled") is True
    assert len(repo2.db["labeling_audit"].items) >= 1
