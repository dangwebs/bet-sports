from __future__ import annotations

import logging
import os
import subprocess
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Rate limiting (admin endpoints)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from src.api.security import require_admin_key
from src.domain.constants import LEAGUES_METADATA
from src.infrastructure.repositories.mongo_repository import get_mongo_repository

_logger = logging.getLogger(__name__)
_BACKEND_DIR = Path(__file__).parent.parent.parent
_training_lock = threading.Lock()
_training_running = False


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class LeagueModel(BaseModel):
    id: str
    name: str
    country: str


class CountryModel(BaseModel):
    name: str
    code: str
    flag: str | None = None
    leagues: list[LeagueModel]


class LeaguesResponse(BaseModel):
    countries: list[CountryModel]
    total_leagues: int


class TeamModel(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    country: str | None = None
    logo_url: str | None = None


class MatchModel(BaseModel):
    id: str
    home_team: TeamModel
    away_team: TeamModel
    league: LeagueModel
    match_date: str
    status: str


class PredictionModel(BaseModel):
    match_id: str
    home_win_probability: float = 0.0
    draw_probability: float = 0.0
    away_win_probability: float = 0.0
    over_25_probability: float = 0.0
    under_25_probability: float = 0.0
    predicted_home_goals: float = 0.0
    predicted_away_goals: float = 0.0
    confidence: float = 0.0
    data_sources: list[str] = Field(default_factory=list)
    recommended_bet: str = ""
    over_under_recommendation: str = ""
    created_at: str = Field(default_factory=_utc_now_iso)
    data_updated_at: str | None = None
    highlights_url: str | None = None
    real_time_odds: dict[str, float] | None = None
    fundamental_analysis: dict[str, bool] | None = None
    suggested_picks: list[dict[str, Any]] = Field(default_factory=list)


class MatchPredictionModel(BaseModel):
    match: MatchModel
    prediction: PredictionModel
    top_ml_picks: list[dict[str, Any]] = Field(default_factory=list)


class PredictionsResponse(BaseModel):
    league: LeagueModel
    predictions: list[MatchPredictionModel]
    generated_at: str


class MatchSuggestedPicksResponse(BaseModel):
    match_id: str
    suggested_picks: list[dict[str, Any]] = Field(default_factory=list)
    combination_warning: str | None = None
    highlights_url: str | None = None
    real_time_odds: dict[str, float] | None = None
    generated_at: str = Field(default_factory=_utc_now_iso)


class BettingFeedbackRequest(BaseModel):
    match_id: str
    market_type: str
    prediction: str
    actual_outcome: str
    was_correct: bool
    odds: float
    stake: float | None = None


class BettingFeedbackResponse(BaseModel):
    success: bool
    message: str
    market_type: str
    new_confidence_adjustment: float


class LearningStatsResponse(BaseModel):
    market_performances: list[dict[str, Any]] = Field(default_factory=list)
    total_feedback_count: int = 0
    last_updated: str = Field(default_factory=_utc_now_iso)


class TrainingStatusPayload(BaseModel):
    status: Literal["IDLE", "IN_PROGRESS", "COMPLETED", "ERROR"]
    message: str
    has_result: bool
    result: dict[str, Any] | None = None
    last_update: str | None = None


class TrainingCachedPayload(BaseModel):
    cached: bool
    data: dict[str, Any] | None = None
    last_update: str | None = None


def _build_leagues_response() -> LeaguesResponse:
    grouped: dict[str, list[LeagueModel]] = defaultdict(list)
    for league_id, metadata in LEAGUES_METADATA.items():
        grouped[metadata["country"]].append(
            LeagueModel(
                id=league_id,
                name=metadata["name"],
                country=metadata["country"],
            )
        )

    countries = [
        CountryModel(
            name=country,
            code=country[:2].upper(),
            leagues=sorted(leagues, key=lambda league: league.name),
        )
        for country, leagues in sorted(grouped.items(), key=lambda item: item[0])
    ]
    return LeaguesResponse(countries=countries, total_leagues=len(LEAGUES_METADATA))


def _find_league(league_id: str) -> LeagueModel:
    metadata = LEAGUES_METADATA.get(league_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Liga no encontrada")
    return LeagueModel(id=league_id, name=metadata["name"], country=metadata["country"])


def _serialize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat() + "Z"
    return str(value)


def _normalize_prediction_document(
    document: dict[str, Any], league: LeagueModel
) -> MatchPredictionModel | None:
    payload = document.get("prediction") or document.get("data") or document
    if not isinstance(payload, dict):
        return None

    match_payload = payload.get("match")
    prediction_payload = payload.get("prediction")

    if not isinstance(match_payload, dict) or not isinstance(prediction_payload, dict):
        return None

    try:
        return MatchPredictionModel.model_validate(
            {
                "match": {
                    **match_payload,
                    "league": match_payload.get("league")
                    or {
                        "id": league.id,
                        "name": league.name,
                        "country": league.country,
                    },
                },
                "prediction": prediction_payload,
                "top_ml_picks": payload.get("top_ml_picks", []),
            }
        )
    except Exception as exc:
        _logger.debug("Failed to normalize prediction document: %s", exc, exc_info=True)
        return None


def _load_predictions_for_league(league_id: str) -> list[MatchPredictionModel]:
    repository = get_mongo_repository()
    league = _find_league(league_id)
    documents = repository.match_predictions.find({"league_id": league_id})
    normalized = [
        parsed
        for parsed in (
            _normalize_prediction_document(document, league) for document in documents
        )
        if parsed is not None
    ]
    return normalized


def _load_training_result() -> tuple[dict[str, Any] | None, str | None]:
    repository = get_mongo_repository()
    result, updated_at = repository.get_training_result_with_timestamp("latest_daily")
    return result, _serialize_timestamp(updated_at)


app = FastAPI(
    title="BJJ-BetSports API",
    version="1.0.0",
    description="API ligera para el stack portable local.",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiter for selective endpoint protection
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    _logger.exception(
        "Unhandled exception on %s %s: %s", request.method, request.url, exc
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=app.version, timestamp=_utc_now_iso())


@app.get("/api/v1/leagues", response_model=LeaguesResponse)
def get_leagues() -> LeaguesResponse:
    return _build_leagues_response()


@app.get("/api/v1/leagues/{league_id}", response_model=LeagueModel)
def get_league(league_id: str) -> LeagueModel:
    return _find_league(league_id)


@app.get("/api/v1/predictions/league/{league_id}", response_model=PredictionsResponse)
def get_predictions_by_league(league_id: str) -> PredictionsResponse:
    league = _find_league(league_id)
    return PredictionsResponse(
        league=league,
        predictions=_load_predictions_for_league(league_id),
        generated_at=_utc_now_iso(),
    )


@app.get("/api/v1/predictions/match/{match_id}", response_model=MatchPredictionModel)
def get_prediction_by_match(match_id: str) -> MatchPredictionModel:
    repository = get_mongo_repository()
    document = repository.match_predictions.find_one({"match_id": match_id})
    if document is None:
        raise HTTPException(status_code=404, detail="Predicción no encontrada")

    league_id = document.get("league_id", "E0")
    normalized = _normalize_prediction_document(document, _find_league(league_id))
    if normalized is None:
        raise HTTPException(status_code=404, detail="Predicción no disponible")
    return normalized


@app.get("/api/v1/matches/live", response_model=list[dict[str, Any]])
def get_live_matches() -> list[dict[str, Any]]:
    return []


@app.get("/api/v1/matches/live/with-predictions", response_model=list[dict[str, Any]])
def get_live_matches_with_predictions() -> list[dict[str, Any]]:
    return []


@app.get("/api/v1/matches/daily", response_model=list[dict[str, Any]])
def get_daily_matches() -> list[dict[str, Any]]:
    return []


@app.get("/api/v1/matches/team/{team_name}", response_model=list[dict[str, Any]])
def get_team_matches(team_name: str) -> list[dict[str, Any]]:
    return []


@app.get(
    "/api/v1/suggested-picks/match/{match_id}",
    response_model=MatchSuggestedPicksResponse,
)
def get_suggested_picks(match_id: str) -> MatchSuggestedPicksResponse:
    return MatchSuggestedPicksResponse(match_id=match_id)


@app.post("/api/v1/suggested-picks/feedback", response_model=BettingFeedbackResponse)
def register_feedback(payload: BettingFeedbackRequest) -> BettingFeedbackResponse:
    return BettingFeedbackResponse(
        success=True,
        message="Feedback registrado",
        market_type=payload.market_type,
        new_confidence_adjustment=0.0,
    )


@app.get("/api/v1/suggested-picks/learning-stats", response_model=LearningStatsResponse)
def get_learning_stats() -> LearningStatsResponse:
    return LearningStatsResponse()


@app.get("/api/v1/train/status", response_model=TrainingStatusPayload)
def get_training_status() -> TrainingStatusPayload:
    if _training_running:
        return TrainingStatusPayload(
            status="IN_PROGRESS",
            message="Entrenamiento en progreso...",
            has_result=False,
            result=None,
            last_update=None,
        )
    result, last_update = _load_training_result()
    if result is None:
        return TrainingStatusPayload(
            status="IDLE",
            message="No hay resultado de entrenamiento disponible todavia.",
            has_result=False,
            result=None,
            last_update=None,
        )
    return TrainingStatusPayload(
        status="COMPLETED",
        message="Resultado de entrenamiento disponible.",
        has_result=True,
        result=result,
        last_update=last_update,
    )


@app.get("/api/v1/train/cached", response_model=TrainingCachedPayload)
def get_training_cached() -> TrainingCachedPayload:
    result, last_update = _load_training_result()
    return TrainingCachedPayload(
        cached=result is not None, data=result, last_update=last_update
    )


@app.post("/api/v1/train/run-now")
@limiter.limit("1/hour")
def trigger_training(admin_key: str = Depends(require_admin_key)) -> dict[str, str]:
    global _training_running
    with _training_lock:
        if _training_running:
            return {
                "status": "already_running",
                "message": "El entrenamiento ya está en progreso.",
            }
        _training_running = True

    n_jobs = os.getenv("N_JOBS", "2")
    train_days = os.getenv("TRAIN_DAYS", "550")
    predict_leagues = os.getenv("PREDICT_LEAGUES", "E0")

    def _run() -> None:
        global _training_running
        try:
            _logger.info(
                "Iniciando entrenamiento: days=%s leagues=%s",
                train_days,
                predict_leagues,
            )
            subprocess.run(
                ["python3", "scripts/orchestrator_cli.py", "cleanup"],
                cwd=str(_BACKEND_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                [
                    "python3",
                    "scripts/orchestrator_cli.py",
                    "train",
                    "--days",
                    train_days,
                    "--n-jobs",
                    n_jobs,
                    "--leagues",
                    predict_leagues,
                ],
                cwd=str(_BACKEND_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            _logger.info("Entrenamiento finalizado.")
        except Exception as exc:
            _logger.error("Error en entrenamiento: %s", exc)
        finally:
            with _training_lock:
                _training_running = False

    threading.Thread(target=_run, daemon=True).start()
    return {
        "status": "started",
        "message": "Entrenamiento iniciado dentro del contenedor.",
    }
