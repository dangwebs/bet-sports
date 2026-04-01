from src.infrastructure.validators.validators import (
    normalize_timestamp_to_iso,
    validate_prediction_payload,
    validate_probability,
)


def test_normalize_timestamp_to_iso():
    iso = normalize_timestamp_to_iso("2026-03-15T12:00:00Z")
    assert iso is not None
    assert ("+00:00" in iso) or iso.endswith("Z")


def test_validate_probability_ok():
    assert validate_probability(0.5) == 0.5


def test_validate_probability_bad():
    import pytest

    with pytest.raises(ValueError):
        validate_probability(1.5)


def test_validate_prediction_payload():
    payload = {
        "prediction": {
            "created_at": "2026-03-15T12:00:00Z",
            "home_win_probability": "0.6",
        }
    }
    out = validate_prediction_payload(payload)
    assert isinstance(out, dict)
    assert out["prediction"]["home_win_probability"] == 0.6
    assert "created_at" in out["prediction"]
