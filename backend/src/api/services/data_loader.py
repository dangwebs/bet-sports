from __future__ import annotations

from datetime import datetime
from typing import Any

from src.api.mappers.league_mapper import find_league
from src.api.mappers.prediction_mapper import normalize_prediction_document
from src.api.schemas.predictions import MatchPredictionModel
from src.api.utils.serializers import _serialize_timestamp
from src.infrastructure.repositories.mongo_repository import get_mongo_repository
from src.utils.time_utils import get_current_time


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
                # Sanity checks: reject matches with dates too far in the past or future
                match_date_str = getattr(parsed.match, "match_date", None)
                if match_date_str:
                    try:
                        dt = datetime.fromisoformat(
                            match_date_str.replace("Z", "+00:00")
                        )
                    except Exception:
                        try:
                            dt = datetime.strptime(match_date_str, "%Y-%m-%d")
                        except Exception:
                            dt = None

                    if dt:
                        now = get_current_time()
                        days_delta = (dt.date() - now.date()).days
                        # Allow predictions within +/-30 days window
                        if days_delta > 30 or days_delta < -30:
                            continue

                normalized.append(parsed)
        return normalized

    def get_latest_training_result(self) -> tuple[dict[str, Any] | None, str | None]:
        result, updated_at = self.repository.get_training_result_with_timestamp(
            "latest_daily"
        )
        return result, _serialize_timestamp(updated_at)
