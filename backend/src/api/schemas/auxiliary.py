from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MatchSuggestedPicksResponse(BaseModel):
    match_id: str
    suggested_picks: list[dict[str, Any]] = Field(default_factory=list)
    combination_warning: str | None = None
    highlights_url: str | None = None
    real_time_odds: dict[str, float] | None = None
    generated_at: str | None = None


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
    last_updated: str | None = None


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
