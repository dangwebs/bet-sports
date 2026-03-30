from datetime import datetime, timedelta, timezone

from src.application.use_cases.use_cases import GetPredictionsUseCase


def test_is_cached_response_stale_false():
    inst = object.__new__(GetPredictionsUseCase)
    db_last_updated = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)
    cached_response = {
        "generated_at": (db_last_updated - timedelta(seconds=5)).isoformat()
    }

    assert inst._is_cached_response_stale(db_last_updated, cached_response) is False


def test_is_cached_response_stale_true():
    inst = object.__new__(GetPredictionsUseCase)
    db_last_updated = datetime(2026, 3, 29, 12, 0, 20, tzinfo=timezone.utc)
    cached_response = {
        "generated_at": (db_last_updated - timedelta(seconds=20)).isoformat()
    }

    assert inst._is_cached_response_stale(db_last_updated, cached_response) is True


def test_normalize_and_apply_probs():
    inst = object.__new__(GetPredictionsUseCase)

    class DummyPrediction:
        def __init__(self):
            self.home_win_probability = 0.0
            self.draw_probability = 0.0
            self.away_win_probability = 0.0
            self.over_25_probability = 0.0
            self.under_25_probability = 0.0
            self.confidence = 0.0
            self.data_sources = []

    pred = DummyPrediction()

    ml_probs = [0.6, 0.2, 0.2, 0.3, 0.7]

    inst._normalize_and_apply_probs(pred, ml_probs)

    # Winner normalization
    assert pred.home_win_probability == round(0.6 / (0.6 + 0.2 + 0.2), 4)
    assert pred.draw_probability == round(0.2 / (0.6 + 0.2 + 0.2), 4)
    assert pred.away_win_probability == round(0.2 / (0.6 + 0.2 + 0.2), 4)

    # Over/Under normalization
    assert pred.over_25_probability == round(0.3 / (0.3 + 0.7), 4)
    assert pred.under_25_probability == round(0.7 / (0.3 + 0.7), 4)

    # Confidence should be the max of normalized probabilities
    expected_conf = max(
        pred.home_win_probability,
        pred.draw_probability,
        pred.away_win_probability,
        pred.over_25_probability,
        pred.under_25_probability,
    )
    assert pred.confidence == expected_conf

    assert "Rigorous ML" in pred.data_sources
