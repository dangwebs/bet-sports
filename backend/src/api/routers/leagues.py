from __future__ import annotations

from fastapi import APIRouter
from src.api.schemas.leagues import LeagueModel, LeaguesResponse
from src.api.utils.helpers import _build_leagues_response, _find_league

router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])


@router.get("/", response_model=LeaguesResponse)
def get_leagues() -> LeaguesResponse:
    return _build_leagues_response()


@router.get("/{league_id}", response_model=LeagueModel)
def get_league(league_id: str) -> LeagueModel:
    return _find_league(league_id)
