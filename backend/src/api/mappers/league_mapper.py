from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from src.api.schemas.leagues import CountryModel, LeagueModel, LeaguesResponse
from src.domain.constants import LEAGUES_METADATA


def build_leagues_response() -> LeaguesResponse:
    grouped: dict[str, list[LeagueModel]] = defaultdict(list)
    for league_id, metadata in LEAGUES_METADATA.items():
        grouped[metadata["country"]].append(
            LeagueModel(
                id=league_id, name=metadata["name"], country=metadata["country"]
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


def find_league(league_id: str) -> LeagueModel:
    metadata = LEAGUES_METADATA.get(league_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Liga no encontrada")
    return LeagueModel(id=league_id, name=metadata["name"], country=metadata["country"])
