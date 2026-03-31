from types import SimpleNamespace

from src.application.services.auto_labeler_rules import derive_market_labels


def test_derive_winner_and_over25():
    match = SimpleNamespace(home_goals=2, away_goals=1)
    doc = {
        "data": {
            "prediction": {
                "home_win_probability": 0.6,
                "draw_probability": 0.2,
                "away_win_probability": 0.2,
                "over_25_probability": 0.7,
            }
        }
    }

    labels = derive_market_labels(doc, match)

    assert "winner" in labels
    winner = labels["winner"]
    assert winner["actual"] == "home_win"
    assert winner["predicted_probability"] == 0.6
    assert winner["predicted_label"] == "home_win"
    assert winner["is_correct"] is True

    assert "over_25" in labels
    over = labels["over_25"]
    assert over["predicted_probability"] == 0.7
    assert over["actual_over"] is True
