from __future__ import annotations

from fastapi import APIRouter
from src.api.schemas.auxiliary import (
    BettingFeedbackRequest,
    BettingFeedbackResponse,
    LearningStatsResponse,
    MatchSuggestedPicksResponse,
)
from src.api.utils.serializers import _utc_now_iso
from src.application.dtos.dtos import BettingFeedbackRequestDTO

# Use application use case to register feedback
from src.application.use_cases.suggested_picks_use_case import RegisterFeedbackUseCase
from src.domain.services.learning_service import LearningService

router = APIRouter(prefix="/api/v1/suggested-picks", tags=["suggested-picks"])


@router.get("/match/{match_id}", response_model=MatchSuggestedPicksResponse)
def get_suggested_picks(match_id: str) -> MatchSuggestedPicksResponse:
    # For now, preserve a safe stub that returns structure expected by frontend.
    return MatchSuggestedPicksResponse(match_id=match_id, generated_at=_utc_now_iso())


@router.post("/feedback", response_model=BettingFeedbackResponse)
def register_feedback(payload: BettingFeedbackRequest) -> BettingFeedbackResponse:
    # Map API payload to application DTO and call RegisterFeedbackUseCase
    dto = BettingFeedbackRequestDTO(**payload.model_dump())
    learning_service = LearningService()
    use_case = RegisterFeedbackUseCase(learning_service)
    resp = use_case.execute(dto)
    return BettingFeedbackResponse(
        success=resp.success,
        message=resp.message,
        market_type=resp.market_type,
        new_confidence_adjustment=resp.new_confidence_adjustment,
    )


@router.get("/learning-stats", response_model=LearningStatsResponse)
def get_learning_stats() -> LearningStatsResponse:
    # Use a best-effort read from LearningService
    service = LearningService()
    stats = service.get_all_stats()
    total_count = sum(p.total_predictions for p in stats.values())
    # Convert to schema-compatible shape; keep minimal for now
    return LearningStatsResponse(
        market_performances=[], total_feedback_count=total_count, last_updated=None
    )
