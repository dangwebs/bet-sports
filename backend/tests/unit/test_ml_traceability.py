from datetime import datetime

from src.application.dtos.dtos import PredictionDTO


def test_prediction_dto_contains_model_metadata():
    md = {
        "model_version": "v1.2.3",
        "training_run": "run-2026-03-31",
        "commit": "abcdef0",
    }

    p = PredictionDTO(
        match_id="m1",
        home_win_probability=0.5,
        draw_probability=0.3,
        away_win_probability=0.2,
        over_25_probability=0.4,
        under_25_probability=0.6,
        predicted_home_goals=1.2,
        predicted_away_goals=0.8,
        predicted_home_corners=3.0,
        predicted_away_corners=2.0,
        predicted_home_yellow_cards=1.0,
        predicted_away_yellow_cards=1.0,
        predicted_home_red_cards=0.0,
        predicted_away_red_cards=0.0,
        confidence=0.75,
        data_sources=["internal"],
        recommended_bet="Home Win (1)",
        over_under_recommendation="Over 2.5",
        suggested_picks=[],
        top_ml_picks=[],
        created_at=datetime.utcnow(),
        model_metadata=md,
    )

    dumped = p.model_dump()
    assert "model_metadata" in dumped
    assert dumped["model_metadata"]["model_version"] == "v1.2.3"
