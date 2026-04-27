"""
Training Data Service

Orchestrates the fetching, merging, and enrichment of training data
from multiple sources (GitHub, CSV, API-Football, ESPN, etc.).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, cast

from src.application.use_cases.use_cases import DataSources
from src.domain.entities.entities import League, Match
from src.domain.services.match_enrichment_service import MatchEnrichmentService
from src.utils.time_utils import COLOMBIA_TZ, get_current_time

logger = logging.getLogger(__name__)


class TrainingDataService:
    """
    Application service for orchestrating training data collection.
    """

    def __init__(
        self, data_sources: DataSources, enrichment_service: MatchEnrichmentService
    ) -> None:
        self.data_sources = data_sources
        self.enrichment_service = enrichment_service

    async def _fetch_github_matches(
        self, leagues: List[str], start_date: Optional[str], days_back: Optional[int]
    ) -> List[Match]:
        """Fetch matches from the GitHub dataset with the same semantics as the
        original inline implementation. Returns empty list on failure."""
        try:
            from src.infrastructure.data_sources.github_dataset import (
                LocalGithubDataSource,
            )

            gh_data = LocalGithubDataSource()
            gh_start_dt = None
            if start_date:
                try:
                    gh_start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError as e:
                    logger.debug(f"GitHub date parsing skipped (invalid format): {e}")
            elif days_back:
                gh_start_dt = get_current_time() - timedelta(days=days_back)

            github_matches = await gh_data.get_finished_matches(
                league_codes=leagues, date_from=gh_start_dt
            )
            return cast(List[Match], github_matches)
        except Exception as e:
            logger.warning(f"GitHub Dataset fetch failed: {e}")
            return []

    async def _fetch_csv_for_league(
        self, lid: str, force_refresh: bool, days_back: Optional[int]
    ) -> List[Match]:
        """Fetch CSV/historical matches for a single league and apply backfill
        when CSV appears stale."""
        try:
            matches = await self.data_sources.football_data_uk.get_historical_matches(
                lid, seasons=None, force_refresh=force_refresh
            )

            if matches:
                matches.sort(key=lambda x: x.match_date)
                last_match_date = matches[-1].match_date

                if last_match_date.tzinfo is None:
                    last_match_date = COLOMBIA_TZ.localize(last_match_date)

                now = get_current_time()
                days_lag = (now - last_match_date).days

                if days_lag > 3:
                    logger.warning(
                        "CSV data for %s is stale (%d days). " "Triggering backfill...",
                        lid,
                        days_lag,
                    )
                    start_backfill = last_match_date + timedelta(days=1)
                    gap_matches = await self._backfill_gap(lid, start_backfill, now)
                    if gap_matches:
                        logger.info(
                            "Backfilled %d matches for %s", len(gap_matches), lid
                        )
                        matches.extend(gap_matches)

            return matches or []
        except Exception as e:
            logger.error(f"Error fetching CSV/Backfill for {lid}: {e}")
            return []

    async def _fetch_football_data_org_matches(
        self, leagues: List[str], days_back: Optional[int]
    ) -> List[Match]:
        try:
            if self.data_sources.football_data_org.is_configured:
                start_dt = get_current_time() - timedelta(days=days_back or 550)
                api_fb_matches = (
                    await self.data_sources.football_data_org.get_finished_matches(
                        date_from=start_dt.strftime("%Y-%m-%d"),
                        date_to=get_current_time().strftime("%Y-%m-%d"),
                        league_codes=leagues,
                    )
                )
                if api_fb_matches:
                    logger.info(
                        f"Football-Data.org: loaded {len(api_fb_matches)} matches"
                    )
                return api_fb_matches or []
        except Exception as e:
            logger.warning(f"Football-Data.org fetch failed: {e}")
        return []

    async def _fetch_espn_matches(self, leagues: List[str]) -> List[Match]:
        try:
            from src.infrastructure.data_sources.espn import ESPNSource

            espn = ESPNSource()
            espn_matches = await espn.get_finished_matches(
                league_codes=leagues, days_back=60
            )
            return espn_matches or []
        except Exception as e:
            logger.warning(f"ESPN fetch failed for training data: {e}")
            return []

    async def _fetch_openfootball_matches(self, leagues: List[str]) -> List[Match]:
        open_football_matches: List[Match] = []
        try:
            from src.infrastructure.data_sources.openfootball import OpenFootballSource

            open_fb = OpenFootballSource()
            for league_code in leagues:
                league_entity = League(
                    id=league_code, name=league_code, country="Europe"
                )
                of_matches = await open_fb.get_matches(league_entity)
                open_football_matches.extend(of_matches)
            if open_football_matches:
                logger.info(
                    f"OpenFootball: loaded {len(open_football_matches)} matches"
                )
            return open_football_matches
        except Exception as e:
            logger.warning(f"OpenFootball fetch failed for training data: {e}")
            return []

    def _get_sortable_date(self, m: Match) -> datetime:
        dt = m.match_date
        if dt.tzinfo is None:
            return cast(datetime, COLOMBIA_TZ.localize(dt))
        return cast(datetime, dt)

    async def fetch_comprehensive_training_data(
        self,
        leagues: List[str],
        days_back: Optional[int] = None,
        start_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[Match]:
        """
        Fetch and unify data from ALL sources for training.
        """
        logger.info(f"Orchestrating comprehensive training data for leagues: {leagues}")

        # Buckets for different sources
        gh_matches = await self._fetch_github_matches(leagues, start_date, days_back)

        # CSV source (parallelized per-league)
        import asyncio

        results = await asyncio.gather(
            *(
                self._fetch_csv_for_league(lid, force_refresh, days_back)
                for lid in leagues
            )
        )
        csv_matches = []
        for res in results:
            csv_matches.extend(res or [])

        api_fb_matches = await self._fetch_football_data_org_matches(leagues, days_back)
        espn_matches = await self._fetch_espn_matches(leagues)
        open_football_matches = await self._fetch_openfootball_matches(leagues)

        # --- UNIFY & ENRICH ---
        all_matches = gh_matches
        all_matches = self.enrichment_service.merge_matches(all_matches, csv_matches)
        all_matches = self.enrichment_service.merge_matches(all_matches, api_fb_matches)
        all_matches = self.enrichment_service.merge_matches(all_matches, espn_matches)
        all_matches = self.enrichment_service.merge_matches(
            all_matches, open_football_matches
        )

        # Sort by standardized date
        all_matches.sort(key=self._get_sortable_date)

        # Final filtering
        if start_date:
            try:
                start_dt = COLOMBIA_TZ.localize(
                    datetime.strptime(start_date, "%Y-%m-%d")
                )
                all_matches = [
                    m for m in all_matches if self._get_sortable_date(m) >= start_dt
                ]
            except ValueError as e:
                logger.debug(f"Start date parsing skipped (invalid format): {e}")
        elif days_back:
            start_dt = get_current_time().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days_back)
            all_matches = [
                m for m in all_matches if self._get_sortable_date(m) >= start_dt
            ]

        logger.info(f"Unification complete: {len(all_matches)} total training matches")
        return all_matches

    async def _backfill_gap(
        self, league_code: str, start_date: datetime, end_date: datetime
    ) -> List[Match]:
        """
        Fetch matches from fallback sources (Football-Data.org, OpenFootball)
        to fill gap between static CSVs and today.
        """
        # Try Football-Data.org first (best recent coverage)
        backfilled = await self._backfill_via_football_data_org(
            league_code, start_date, end_date
        )
        if backfilled:
            return backfilled

        # Fallback: try OpenFootball for historical seasons
        backfilled = await self._backfill_via_openfootball(
            league_code, start_date, end_date
        )
        return backfilled

    async def _backfill_via_football_data_org(
        self, league_code: str, start_date: datetime, end_date: datetime
    ) -> List[Match]:
        try:
            if self.data_sources.football_data_org.is_configured:
                logger.info(
                    "Backfilling %s via Football-Data.org from %s to %s...",
                    league_code,
                    start_date.date(),
                    end_date.date(),
                )
                fd_matches = (
                    await self.data_sources.football_data_org.get_finished_matches(
                        date_from=start_date.strftime("%Y-%m-%d"),
                        date_to=end_date.strftime("%Y-%m-%d"),
                        league_codes=[league_code],
                    )
                )
                typed_matches = cast(List[Match], fd_matches)
                if typed_matches:
                    logger.info(
                        "✓ Found %d backfill matches in Football-Data.org for %s",
                        len(typed_matches),
                        league_code,
                    )
                    return typed_matches
                else:
                    logger.info(
                        f"No matches found in Football-Data.org for {league_code} gap."
                    )
        except Exception as e:
            logger.warning(
                f"Backfill source Football-Data.org failed for {league_code}: {e}"
            )
        return []

    async def _backfill_via_openfootball(
        self, league_code: str, start_date: datetime, end_date: datetime
    ) -> List[Match]:
        try:
            from src.domain.entities.entities import League
            from src.infrastructure.data_sources.football_data_uk import (
                LEAGUES_METADATA,
            )

            if league_code in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[league_code]
                league = League(
                    id=league_code, name=meta["name"], country=meta["country"]
                )

                of_matches = await self.data_sources.openfootball.get_matches(league)

                relevant_matches = []
                for m in of_matches:
                    m_date = m.match_date
                    if m_date.tzinfo is None and start_date.tzinfo:
                        m_date = COLOMBIA_TZ.localize(m_date)
                    if start_date <= m_date <= end_date:
                        relevant_matches.append(m)

                if relevant_matches:
                    logger.info(
                        "✓ Found %d backfill matches in OpenFootball for %s",
                        len(relevant_matches),
                        league_code,
                    )
                    return relevant_matches
        except Exception as e:
            logger.warning(
                f"Backfill source OpenFootball failed for {league_code}: {e}"
            )
        return []
