from __future__ import annotations

from typing import Any

from src.api.mappers.league_mapper import find_league
from src.api.mappers.prediction_mapper import normalize_prediction_document
from src.api.schemas.predictions import MatchPredictionModel
from src.api.utils.serializers import _serialize_timestamp
from src.infrastructure.repositories.mongo_repository import get_mongo_repository


class DataLoader:
    def __init__(self, repository=None) -> None:
        self.repository = repository or get_mongo_repository()

    def load_predictions_for_league(self, league_id: str) -> list[MatchPredictionModel]:
        league = find_league(league_id)
        documents = self.repository.match_predictions.find({"league_id": league_id})
        normalized: list[MatchPredictionModel] = []
        for document in documents:
            parsed = normalize_prediction_document(document, league)
            if parsed is not None:
                normalized.append(parsed)
        return normalized

    def get_latest_training_result(self) -> tuple[dict[str, Any] | None, str | None]:
        result, updated_at = self.repository.get_training_result_with_timestamp(
            "latest_daily"
        )
        return result, _serialize_timestamp(updated_at)
