from __future__ import annotations

from typing import Any

# Delegate implementation to mappers and services for clearer separation
from src.api.schemas.predictions import MatchPredictionModel
from src.api.services.data_loader import DataLoader

# Wrapper that keeps the same public API as before while delegating
# to the new modules (backwards-compatible)


def _load_predictions_for_league(league_id: str) -> list[MatchPredictionModel]:
    loader = DataLoader()
    return loader.load_predictions_for_league(league_id)


def _load_training_result() -> tuple[dict[str, Any] | None, str | None]:
    loader = DataLoader()
    return loader.get_latest_training_result()
