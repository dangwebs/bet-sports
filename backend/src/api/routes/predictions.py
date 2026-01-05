"""
Predictions Router

API endpoints for getting match predictions.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import ORJSONResponse

from src.application.dtos.dtos import (
    PredictionsResponseDTO,
    MatchPredictionDTO,
    ErrorResponseDTO,
    SortBy,
)
from src.api.dependencies import get_data_sources, get_prediction_service

import logging
logger = logging.getLogger(__name__)



router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get(
    "/league/{league_id}",
    response_model=PredictionsResponseDTO,
    response_class=ORJSONResponse,
    responses={
        404: {"model": ErrorResponseDTO, "description": "League not found or no forecast available"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get predictions for a league",
    description="Returns match predictions for upcoming matches. Priorities: Ephemeral Cache -> Persistent DB -> Real-time Calculation.",
)
async def get_league_predictions(
    league_id: str,
) -> PredictionsResponseDTO:
    """Get predictions for a league with multi-layer fallback."""
    from src.api.dependencies import (
        get_data_sources, get_prediction_service, 
        get_background_processor, get_statistics_service,
        get_persistence_repository, get_risk_manager,
        get_match_aggregator_service
    )
    from src.application.use_cases.use_cases import GetPredictionsUseCase
    from src.domain.services.team_service import TeamService
    
    try:
        # GetPredictionsUseCase now handles Cache -> DB logic internally
        use_case = GetPredictionsUseCase(
            data_sources=get_data_sources(),
            prediction_service=get_prediction_service(),
            statistics_service=get_statistics_service(),
            match_aggregator=get_match_aggregator_service(),
            risk_manager=get_risk_manager(),
            persistence_repository=get_persistence_repository(),
            background_processor=get_background_processor()
        )
        
        result = await use_case.execute(league_id, limit=30)
        
        # POST-PROCESS: Inject logos into cached data that may be missing them
        for pred in result.predictions:
            if pred.match.home_team:
                if not pred.match.home_team.logo_url:
                    pred.match.home_team.logo_url = TeamService.get_team_logo(pred.match.home_team.name)
            if pred.match.away_team:
                if not pred.match.away_team.logo_url:
                    pred.match.away_team.logo_url = TeamService.get_team_logo(pred.match.away_team.name)
        
        if not result.predictions:
            logger.warning(f"No predictions found for {league_id}")
            # We still return the empty DTO rather than 404 to avoid frontend errors
            # but we could raise 404 if preferred.
            
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch predictions for {league_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error serving predictions for {league_id}: {str(e)}"
        )



@router.get(
    "/match/{match_id}",
    response_model=MatchPredictionDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "Match not found or no forecast available"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get prediction for a specific match (Pre-calculated)",
    description="Returns pre-calculated prediction for a specific match by ID. Checks Cache -> DB.",
)
async def get_match_prediction(match_id: str) -> MatchPredictionDTO:
    """Get pre-calculated prediction for a specific match from local cache or DB."""
    from src.infrastructure.cache.cache_service import get_cache_service
    from src.infrastructure.repositories.persistence_repository import get_persistence_repository
    
    cache = get_cache_service()
    repo = get_persistence_repository()
    
    # Key format: forecasts:match_{match_id}
    cache_key = f"forecasts:match_{match_id}"
    
    # 1. Try Cache
    cached_match = cache.get(cache_key)
    if cached_match:
        if isinstance(cached_match, dict):
            return MatchPredictionDTO(**cached_match)
        # If it's already an object (unlikely with simple cache but possible)
        return cached_match
        
    # 2. Try DB (Persistence Repository)
    if repo:
        try:
            db_data, _ = repo.get_match_prediction_with_timestamp(match_id)
            if db_data:
                # Cache it for next time (short TTL e.g. 5 min to allow updates)
                cache.set(cache_key, db_data, ttl_seconds=300)
                return MatchPredictionDTO(**db_data)
        except Exception as e:
            logger.error(f"Error fetching match {match_id} from DB: {e}")
            
    raise HTTPException(
        status_code=404, 
        detail=f"No pre-calculated forecast available for match {match_id}. Ensure the daily job has run."
    )
