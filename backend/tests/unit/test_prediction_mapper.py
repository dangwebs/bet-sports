from src.api.mappers.prediction_mapper import normalize_prediction_document
from src.api.schemas.leagues import LeagueModel


def test_normalize_prediction_document_basic():
    doc = {
        "prediction": {
            "match": {
                "id": "m1",
                "match_date": "2026-03-31T12:00:00Z",
                "home_team": {"id": "h1", "name": "Home FC"},
                "away_team": {"id": "a1", "name": "Away FC"},
                "status": "scheduled",
            },
            "prediction": {
                "match_id": "m1",
                "home_win_probability": 0.6,
                "away_win_probability": 0.4,
            },
            "top_ml_picks": [{"pick": "home", "confidence": 0.6}],
        }
    }

    league = LeagueModel(id="E0", name="Premier League", country="England")
    normalized = normalize_prediction_document(doc, league)
    assert normalized is not None
    assert normalized.match.id == "m1"
    assert normalized.match.league.id == "E0"
    assert normalized.prediction is not None
