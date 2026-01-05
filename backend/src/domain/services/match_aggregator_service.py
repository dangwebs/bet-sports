"""
Match Aggregator Service

This domain service is responsible for:
1. Fetching historical matches from all available data sources (UK, Org, Open) in parallel.
2. Fetching upcoming matches from all available data sources.
3. Merging and deduplicating match data, prioritizing richest data sources.
4. Implementing strict aggregation rules as per project standards.
5. Enforcing Data Sanity (Refactoring Rule 13).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.entities.entities import Match, League
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
from src.utils.time_utils import get_current_time

logger = logging.getLogger(__name__)

class MatchAggregatorService:
    def __init__(
        self,
        football_data_uk: FootballDataUKSource,
        football_data_org: FootballDataOrgSource,
        openfootball: OpenFootballSource,
        thesportsdb: TheSportsDBClient
    ):
        self.football_data_uk = football_data_uk
        self.football_data_org = football_data_org
        self.openfootball = openfootball
        self.thesportsdb = thesportsdb

    async def get_aggregated_history(self, league_id: str, seasons: List[str]) -> List[Match]:
        """
        Fetch historical matches from ALL sources in parallel, merge them, and validate sanity.
        """
        logger.info(f"Aggregating history for {league_id} from all sources...")
        
        # Define parallel tasks
        tasks = []
        
        # 1. Football-Data.co.uk (Primary)
        tasks.append(self.football_data_uk.get_historical_matches(
            league_id,
            seasons=seasons,
        ))
        
        # 2. Football-Data.org (Secondary)
        if self.football_data_org.is_configured:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
            tasks.append(self.football_data_org.get_finished_matches(
                date_from=start_date.strftime("%Y-%m-%d"),
                date_to=end_date.strftime("%Y-%m-%d"),
                league_codes=[league_id]
            ))
        else:
            tasks.append(asyncio.sleep(0))
            
        # 3. OpenFootball (Fallback)
        from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
        if self.openfootball and league_id in LEAGUES_METADATA:
            meta = LEAGUES_METADATA[league_id]
            league_entity = League(id=league_id, name=meta["name"], country=meta["country"])
            tasks.append(self.openfootball.get_matches(league_entity))
        else:
             tasks.append(asyncio.sleep(0))
        
        # Execute
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        uk_matches = results[0] if not isinstance(results[0], Exception) else []
        org_matches = results[1] if not isinstance(results[1], Exception) and results[1] is not None else []
        open_matches = results[2] if not isinstance(results[2], Exception) and results[2] is not None else []
        
        if isinstance(results[0], Exception): logger.warning(f"UK Source Error: {results[0]}")

        # Merge
        merged_matches = self._merge_matches(uk_matches, org_matches, open_matches)
        
        # Validate Sanity (Rule 13)
        valid_matches = []
        rejected_count = 0
        for m in merged_matches:
            if self._is_data_sane(m):
                valid_matches.append(m)
            else:
                rejected_count += 1
                
        if rejected_count > 0:
            logger.warning(f"Rejected {rejected_count} matches due to Data Sanity violations (Outliers).")
            
        return valid_matches

    def _is_data_sane(self, match: Match) -> bool:
        """
        Rule 13: Data Sanity / Outlier Detection.
        Returns False if match data implies corruption or absurdity.
        """
        # 1. Goal Sanity
        total_goals = (match.home_goals or 0) + (match.away_goals or 0)
        if total_goals > 20: # Example threshold: >20 goals is likely bad data 
            return False
            
        # 2. Score Sanity (Negative scores)
        if (match.home_goals is not None and match.home_goals < 0) or \
           (match.away_goals is not None and match.away_goals < 0):
            return False
            
        # 3. Date sanity (Future date for finished match?)
        # if match.status == "FT" and match.match_date > datetime.now(...) # Handled elsewhere usually

        return True

    def _merge_matches(self, uk: List[Match], org: List[Match], open_src: List[Match]) -> List[Match]:
        """Merge strategy: UK > Org > Open."""
        merged = {}
        
        def process_list(matches, source_tag):
            count = 0
            if not matches: return count
            for m in matches:
                if m.status not in ["FT", "AET", "PEN", "FINISHED"]: continue
                if not m.match_date: continue
                
                key = f"{m.match_date.strftime('%Y%m%d')}_{m.home_team.name.lower()}_{m.away_team.name.lower()}"
                
                if key not in merged:
                    merged[key] = m
                    count += 1
            return count

        c_uk = process_list(uk or [], "UK")
        c_org = process_list(org or [], "Org")
        c_open = process_list(open_src or [], "Open")
        
        logger.info(f"Merged History: UK={c_uk}, Org={c_org}, Open={c_open}. Total={len(merged)}")
        return list(merged.values())

    async def get_upcoming_matches(self, league_id: str, limit: int = 20) -> List[Match]:
        """
        Fetch upcoming matches from available sources.
        """
        # Try Football-Data.org
        if self.football_data_org.is_configured:
            matches = await self.football_data_org.get_upcoming_matches(league_id)
            if matches:
                 return self._sort_and_limit(matches, limit)
        
        # Try TheSportsDB
        try:
            matches = await self.thesportsdb.get_upcoming_fixtures(league_id, next_n=limit)
            if matches:
                 return self._sort_and_limit(matches, limit)
        except Exception:
             pass
             
        # Try OpenFootball
        try:
             from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
             if self.openfootball and league_id in LEAGUES_METADATA:
                 meta = LEAGUES_METADATA[league_id]
                 league_entity = League(id=league_id, name=meta["name"], country=meta["country"])
                 matches = await self.openfootball.get_matches(league_entity)
                 upcoming = [m for m in matches if m.status == "NS"]
                 if upcoming:
                     return self._sort_and_limit(upcoming, limit)
        except Exception:
            pass
            
        return []

    def _sort_and_limit(self, matches: List[Match], limit: int) -> List[Match]:
        """Helper to strict sort by date and limit. Includes Sanity Check."""
        now = get_current_time()
        valid = []
        for m in matches:
             # Sanity Check for Upcoming
             odds_sane = True
             # Check odds if present (e.g. < 1.01) - Not always available in 'Match' entity here, usually later in Enrichment
             
             m_date = m.match_date
             if m_date.tzinfo is None:
                 m_date = now.tzinfo.localize(m_date)
             else:
                 m_date = m_date.astimezone(now.tzinfo)
             
             if m_date > now and odds_sane:
                 valid.append(m)
        
        valid.sort(key=lambda x: x.match_date)
        return valid[:limit]
