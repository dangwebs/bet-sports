from __future__ import annotations

from fastapi import APIRouter, HTTPException
from src.api.mappers.league_mapper import find_league
from src.api.mappers.prediction_mapper import normalize_prediction_document
from src.api.schemas.predictions import MatchPredictionModel, PredictionsResponse
from src.api.services.data_loader import DataLoader
from src.api.utils.serializers import _utc_now_iso
from src.infrastructure.repositories.mongo_repository import get_mongo_repository

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("/league/{league_id}", response_model=PredictionsResponse)
def get_predictions_by_league(league_id: str) -> PredictionsResponse:
    loader = DataLoader()
    league = find_league(league_id)
    return PredictionsResponse(
        league=league,
        predictions=loader.load_predictions_for_league(league_id),
        generated_at=_utc_now_iso(),
    )


@router.get("/match/{match_id}", response_model=MatchPredictionModel)
def get_prediction_by_match(match_id: str) -> MatchPredictionModel:
    repository = get_mongo_repository()
    document = repository.match_predictions.find_one({"match_id": match_id})
    if document is None:
        raise HTTPException(status_code=404, detail="Predicción no encontrada")

    league_id = document.get("league_id", "E0")
    normalized = normalize_prediction_document(document, find_league(league_id))
    if normalized is None:
        raise HTTPException(status_code=404, detail="Predicción no disponible")
    return normalized
