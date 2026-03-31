from src.api.mappers.league_mapper import build_leagues_response, find_league
from src.domain.constants import LEAGUES_METADATA


def test_build_leagues_response_contains_metadata():
    resp = build_leagues_response()
    assert resp.total_leagues == len(LEAGUES_METADATA)


def test_find_league_valid():
    # pick a known league id from constants
    league_id = next(iter(LEAGUES_METADATA.keys()))
    league = find_league(league_id)
    assert league.id == league_id
