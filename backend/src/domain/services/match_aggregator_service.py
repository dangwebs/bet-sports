"""
Match Aggregator Service

This domain service is responsible for:
1. Fetching historical matches from all available data sources (UK, Org, Open) in parallel.
2. Fetching upcoming matches from all available data sources.
3. Merging and deduplicating match data, prioritizing richest data sources.
4. Implementing strict aggregation rules as per project standards.
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
        Fetch historical matches from ALL sources in parallel and merge them.
        Priority: FootballDataUK (Rich Stats) > FootballDataOrg (Verified Status) > OpenFootball (Fallback).
        """
        logger.info(f"Aggregating history for {league_id} from all sources...")
        
        # Define parallel tasks
        tasks = []
        
        # 1. Football-Data.co.uk (Primary - Rich Stats: Corners, Cards, Odds)
        tasks.append(self.football_data_uk.get_historical_matches(
            league_id,
            seasons=seasons,
        ))
        
        # 2. Football-Data.org (Secondary - Reliable Status/Scores)
        if self.football_data_org.is_configured:
            # Org API uses dates. Approximate last 2 years.
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
            tasks.append(self.football_data_org.get_finished_matches(
                date_from=start_date.strftime("%Y-%m-%d"),
                date_to=end_date.strftime("%Y-%m-%d"),
                league_codes=[league_id]
            ))
        else:
            tasks.append(asyncio.sleep(0)) # No-op
            
        # 3. OpenFootball (Fallback - Git JSON)
        # Requires League Entity mapping internally or we mock it minimal
        # The use case passed 'league' entity before, but here we might need to recreate it or fetch it.
        # Ideally, OpenFootball source should accept league_id if it maps it internally, 
        # but existing signature is get_matches(league: League).
        # We will create a robust placeholder league entity for the call.
        from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
        if self.openfootball and league_id in LEAGUES_METADATA:
            meta = LEAGUES_METADATA[league_id]
            # Create minimal league entity for query
            league_entity = League(id=league_id, name=meta["name"], country=meta["country"])
            tasks.append(self.openfootball.get_matches(league_entity))
        else:
             tasks.append(asyncio.sleep(0))
        
        # Execute
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Unpack
        uk_matches = results[0] if not isinstance(results[0], Exception) else []
        org_matches = results[1] if not isinstance(results[1], Exception) and results[1] is not None else []
        open_matches = results[2] if not isinstance(results[2], Exception) and results[2] is not None else []
        
        # Log Errors
        if isinstance(results[0], Exception): logger.warning(f"UK Source Error: {results[0]}")
        if isinstance(results[1], Exception): logger.warning(f"Org Source Error: {results[1]}")
        if isinstance(results[2], Exception): logger.warning(f"Open Source Error: {results[2]}")

        return self._merge_matches(uk_matches, org_matches, open_matches)

    def _merge_matches(self, uk: List[Match], org: List[Match], open_src: List[Match]) -> List[Match]:
        """Merge strategy: UK > Org > Open."""
        merged = {}
        
        def process_list(matches, source_tag):
            count = 0
            if not matches: return count
            for m in matches:
                # Filter strictly for finished matches
                if m.status not in ["FT", "AET", "PEN", "FINISHED"]: continue
                
                # Deduplication Key: YYYYMMDD_Home_Away
                # Normalize names (lowercase, remove spaces? strict fuzzy? for now simple Lower)
                # Ensure date is available
                if not m.match_date: continue
                
                key = f"{m.match_date.strftime('%Y%m%d')}_{m.home_team.name.lower()}_{m.away_team.name.lower()}"
                
                # Priority Logic
                # Since we process in order of priority (UK called first, etc), 
                # we can just 'setdefault' or overwrite if we want to support backfilling.
                # Here, simpler is: if not exists, add.
                # BUT, wait. I want UK to be #1. So if I process UK first, strict 'setdefault' works.
                if key not in merged:
                    merged[key] = m
                    count += 1
            return count

        c_uk = process_list(uk or [], "UK")
        
        # Org second. If key exists (from UK), we SKIP Org (because UK has corners).
        # If key doesn't exist (UK missed it), we take Org.
        c_org = process_list(org or [], "Org")
        
        # Open third.
        c_open = process_list(open_src or [], "Open")
        
        logger.info(f"Merged History: UK={c_uk}, Org={c_org}, Open={c_open}. Total={len(merged)}")
        return list(merged.values())

    async def get_upcoming_matches(self, league_id: str, limit: int = 20) -> List[Match]:
        """
        Fetch upcoming matches from available sources.
        Priority: FootballDataOrg (Best Schedule) > TheSportsDB > OpenFootball.
        """
        # Try Football-Data.org first
        if self.football_data_org.is_configured:
            matches = await self.football_data_org.get_upcoming_matches(league_id)
            if matches:
                 return self._sort_and_limit(matches, limit)
        
        # Try TheSportsDB
        try:
            matches = await self.thesportsdb.get_upcoming_fixtures(league_id, next_n=limit)
            if matches:
                 return self._sort_and_limit(matches, limit)
        except Exception as e:
             logger.warning(f"TheSportsDB fetch failed: {e}")
             
        # Try OpenFootball
        try:
             # We need to rely on metadata mapping again
             from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
             if self.openfootball and league_id in LEAGUES_METADATA:
                 meta = LEAGUES_METADATA[league_id]
                 league_entity = League(id=league_id, name=meta["name"], country=meta["country"])
                 matches = await self.openfootball.get_matches(league_entity)
                 # Filter NS
                 upcoming = [m for m in matches if m.status == "NS"]
                 if upcoming:
                     return self._sort_and_limit(upcoming, limit)
        except Exception as e:
            logger.error(f"OpenFootball fetch failed: {e}")
            
        return []

    def _sort_and_limit(self, matches: List[Match], limit: int) -> List[Match]:
        """Helper to strict sort by date and limit."""
        # Filter past matches? Strict validation
        now = get_current_time() # Local time (Bogota)
        
        valid = []
        for m in matches:
             m_date = m.match_date
             if m_date.tzinfo is None:
                 m_date = now.tzinfo.localize(m_date)
             else:
                 m_date = m_date.astimezone(now.tzinfo)
             
             if m_date > now:
                 valid.append(m)
        
        valid.sort(key=lambda x: x.match_date)
        return valid[:limit]
