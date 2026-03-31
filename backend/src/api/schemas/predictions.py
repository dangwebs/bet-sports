from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from src.api.schemas.leagues import LeagueModel
from src.api.utils.serializers import _utc_now_iso


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
