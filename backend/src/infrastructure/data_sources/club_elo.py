"""
ClubElo Data Source

Fetches football Elo ratings from api.clubelo.com.
Provides a global, objective measure of team strength.
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)


class ClubEloSource:
    BASE_URL = "http://api.clubelo.com"
    _cache: Dict[str, float] = {}
    _last_fetch: Optional[datetime] = None

    async def get_elo_for_match(
        self,
        home_team: str,
        away_team: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Get Elo ratings for home and away teams.

        Returns a tuple (home_elo, away_elo).
        """
        await self._ensure_cache()

        h_elo = self._find_team_elo(home_team)
        a_elo = self._find_team_elo(away_team)

        return h_elo, a_elo

    async def _ensure_cache(self) -> None:
        """Fetch and cache the latest Elo ratings (once per day)."""
        now = datetime.now()
        if self._last_fetch and (now - self._last_fetch) < timedelta(hours=24):
            return
        # Retry with exponential backoff (resilience improvement)
        max_retries = 3
        backoff_delay = 2  # seconds

        import asyncio

        for attempt in range(max_retries):
            try:
                # Lazy import pandas (only when fetching data)
                import pandas as pd

                # Fetch current ratings for all teams
                url = f"{self.BASE_URL}/{now.strftime('%Y-%m-%d')}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            # Parse CSV
                            df = pd.read_csv(io.StringIO(content))
                            # Cache: {TeamName: Elo}
                            self._cache = dict(zip(df["Club"], df["Elo"]))
                            self._last_fetch = now
                            logger.info(
                                "Fetched %d ClubElo ratings",
                                len(self._cache),
                            )
                            return

                        logger.warning(
                            "Failed to fetch ClubElo (status %s) " "attempt %d/%d",
                            response.status,
                            attempt + 1,
                            max_retries,
                        )

            except Exception as e:  # pragma: no cover
                # network/IO retry handling
                logger.error(
                    "Error fetching ClubElo data (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    e,
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2

        # Fallback if all retries fail
        logger.error(
            "ClubElo fetch failed after all retries. " "Using cached or empty data."
        )

    def _find_team_elo(self, team_name: str) -> Optional[float]:
        """Fuzzy search for team name in Elo cache."""
        if not self._cache:
            return None

        # 1. Direct match
        if team_name in self._cache:
            return self._cache[team_name]

        # 2. Normalized match
        normalized_input = team_name.lower().replace(" ", "")

        # Try to find best match. This is a simple heuristic
        # and may be improved.
        for club, elo in self._cache.items():
            normalized_club = club.lower().replace(" ", "")
            if normalized_input == normalized_club:
                return elo

            if (
                normalized_input in normalized_club
                or normalized_club in normalized_input
            ):
                # Accept only if length difference < 4 to avoid false positives
                if abs(len(normalized_input) - len(normalized_club)) < 4:
                    return elo

        return None
