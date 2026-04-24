"""
ESPN API Data Source

This module integrates with ESPN's hidden public API for soccer scores and stats.
Provides free access to real-time and historical match data with detailed stats.

Endpoints:
- Scoreboard: http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard
- Summary: http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from src.domain.entities.entities import League, Match, Team
from src.domain.services.team_service import TeamService

logger = logging.getLogger(__name__)

# Mapping internal league codes to ESPN league slugs
ESPN_LEAGUE_MAPPING = {
    # England
    "E0": "eng.1",
    "E1": "eng.2",
    "E_FA": "eng.fa",
    "E2": "eng.3",
    "E3": "eng.4",
    # Spain
    "SP1": "esp.1",
    "SP2": "esp.2",
    "SP_C": "esp.copa_del_rey",
    # Germany
    "D1": "ger.1",
    "D2": "ger.2",
    # Italy
    "I1": "ita.1",
    "I2": "ita.2",
    # France
    "F1": "fra.1",
    "F2": "fra.2",
    # Others
    "B1": "bel.1",
    "B2": "bel.2",
    "P1": "por.1",
    "P2": "por.2",
    "N1": "ned.1",
    "N2": "ned.2",
    # International Tournaments
    "UCL": "uefa.champions",
    "UEL": "uefa.europa",
    "UECL": "uefa.europa.conf",
    "EURO": "uefa.euro",
    "WC": "fifa.world",
    # South America
    "LIB": "conmebol.libertadores",
    "SUD": "conmebol.sudamericana",
    "COL1": "col.1",
    "ARG1": "arg.1",
    "BRA1": "bra.1",
}


@dataclass
class ESPNMatchStats:
    """Container for ESPN advanced match statistics."""

    # Basic
    possession_home: Optional[str] = None
    possession_away: Optional[str] = None
    # Shots
    total_shots_home: Optional[int] = None
    total_shots_away: Optional[int] = None
    shots_on_target_home: Optional[int] = None
    shots_on_target_away: Optional[int] = None
    # Passes
    total_passes_home: Optional[int] = None
    total_passes_away: Optional[int] = None
    pass_accuracy_home: Optional[str] = None
    pass_accuracy_away: Optional[str] = None
    # Defensive
    tackles_home: Optional[int] = None
    tackles_away: Optional[int] = None
    interceptions_home: Optional[int] = None
    interceptions_away: Optional[int] = None
    # Corners/Cards (already in Match, but for completeness)
    corners_home: Optional[int] = None
    corners_away: Optional[int] = None
    yellow_cards_home: Optional[int] = None
    yellow_cards_away: Optional[int] = None
    red_cards_home: Optional[int] = None
    red_cards_away: Optional[int] = None
    fouls_home: Optional[int] = None
    fouls_away: Optional[int] = None


@dataclass
class ESPNOdds:
    """Container for ESPN betting odds."""

    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    over_under_line: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    provider: Optional[str] = None


@dataclass
class ESPNLineup:
    """Container for team lineup information."""

    team_id: str
    team_name: str
    formation: Optional[str] = None
    starters: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.starters is None:
            self.starters = []


class ESPNSource:
    """
    Data source for ESPN API.
    """

    SOURCE_NAME = "ESPN"
    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/soccer"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _make_request(
        self, url: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        """Make HTTP request to ESPN."""
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"ESPN request failed: {e}")
            return None

    async def get_match_summary(
        self, league_code: str, event_id: str
    ) -> Optional[dict]:
        """
        Fetch full match summary from ESPN.
        Returns raw JSON for flexible parsing.
        """
        slug = ESPN_LEAGUE_MAPPING.get(league_code)
        if not slug:
            return None
        url = f"{self.BASE_URL}/{slug}/summary"
        return await self._make_request(url, {"event": event_id})

    async def get_match_advanced_stats(
        self, league_code: str, event_id: str
    ) -> Optional[ESPNMatchStats]:
        """
        Extract advanced match statistics from ESPN summary.
        """
        data = await self.get_match_summary(league_code, event_id)
        if not data:
            return None

        boxscore = data.get("boxscore", {})
        teams = boxscore.get("teams", [])

        if len(teams) < 2:
            return None

        def get_stat(team_data: dict, stat_name: str) -> Optional[str]:
            for s in team_data.get("statistics", []):
                if s.get("name") == stat_name:
                    return s.get("displayValue")
            return None

        def p_int(val: str) -> Optional[int]:
            try:
                return int(float(val)) if val else None
            except Exception:
                return None

        # Determine home/away from rosters or header
        home_idx = 0
        away_idx = 1
        rosters = data.get("rosters", [])
        if rosters and len(rosters) >= 2:
            if rosters[0].get("homeAway") == "away":
                home_idx, away_idx = 1, 0

        home = teams[home_idx] if home_idx < len(teams) else {}
        away = teams[away_idx] if away_idx < len(teams) else {}

        return ESPNMatchStats(
            possession_home=get_stat(home, "possessionPct"),
            possession_away=get_stat(away, "possessionPct"),
            total_shots_home=p_int(get_stat(home, "totalShots")),
            total_shots_away=p_int(get_stat(away, "totalShots")),
            shots_on_target_home=p_int(get_stat(home, "shotsOnTarget")),
            shots_on_target_away=p_int(get_stat(away, "shotsOnTarget")),
            total_passes_home=p_int(get_stat(home, "totalPasses")),
            total_passes_away=p_int(get_stat(away, "totalPasses")),
            pass_accuracy_home=get_stat(home, "passPct"),
            pass_accuracy_away=get_stat(away, "passPct"),
            tackles_home=p_int(get_stat(home, "effectiveTackles")),
            tackles_away=p_int(get_stat(away, "effectiveTackles")),
            interceptions_home=p_int(get_stat(home, "interceptions")),
            interceptions_away=p_int(get_stat(away, "interceptions")),
            corners_home=p_int(get_stat(home, "wonCorners")),
            corners_away=p_int(get_stat(away, "wonCorners")),
            yellow_cards_home=p_int(get_stat(home, "yellowCards")),
            yellow_cards_away=p_int(get_stat(away, "yellowCards")),
            red_cards_home=p_int(get_stat(home, "redCards")),
            red_cards_away=p_int(get_stat(away, "redCards")),
            fouls_home=p_int(get_stat(home, "foulsCommitted")),
            fouls_away=p_int(get_stat(away, "foulsCommitted")),
        )

    async def get_match_odds(
        self, league_code: str, event_id: str
    ) -> Optional[ESPNOdds]:
        """
        Extract betting odds from ESPN match summary (pickcenter).
        """
        data = await self.get_match_summary(league_code, event_id)
        if not data:
            return None

        pickcenter = data.get("pickcenter", [])
        if not pickcenter:
            return None

        # pickcenter is usually a list of providers
        # We take the first one
        pick = pickcenter[0] if pickcenter else {}

        # ESPN format varies; common fields: homeTeamOdds, awayTeamOdds, drawOdds
        home_odds_data = pick.get("homeTeamOdds", {})
        away_odds_data = pick.get("awayTeamOdds", {})

        h_val = home_odds_data.get("moneyLine") or home_odds_data.get("value")
        a_val = away_odds_data.get("moneyLine") or away_odds_data.get("value")
        d_val = pick.get("drawOdds", {}).get("value")

        return ESPNOdds(
            home_odds=h_val,
            draw_odds=d_val,
            away_odds=a_val,
            over_under_line=pick.get("overUnder"),
            over_odds=pick.get("overOdds"),
            under_odds=pick.get("underOdds"),
            provider=pick.get("provider", {}).get("name"),
        )

    async def get_match_lineups(
        self, league_code: str, event_id: str
    ) -> tuple[Optional[ESPNLineup], Optional[ESPNLineup]]:
        """
        Extract lineups and formations from ESPN match summary.
        Returns (home_lineup, away_lineup).
        """
        data = await self.get_match_summary(league_code, event_id)
        if not data:
            return None, None

        rosters = data.get("rosters", [])
        if len(rosters) < 2:
            return None, None

        home_lineup = None
        away_lineup = None

        for roster in rosters:
            is_home = roster.get("homeAway") == "home"
            team_info = roster.get("team", {})

            lineup = ESPNLineup(
                team_id=team_info.get("id", ""),
                team_name=team_info.get("displayName", ""),
                formation=roster.get("formation"),
                starters=[
                    {
                        "id": p.get("athlete", {}).get("id"),
                        "name": p.get("athlete", {}).get("displayName"),
                        "position": p.get("position", {}).get("abbreviation"),
                        "jersey": p.get("athlete", {}).get("jersey"),
                    }
                    for p in roster.get("roster", [])
                    if p.get("starter")
                ],
            )

            if is_home:
                home_lineup = lineup
            else:
                away_lineup = lineup

        return home_lineup, away_lineup

    async def get_finished_matches(
        self,
        league_codes: Optional[List[str]] = None,
        days_back: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Match]:
        """
        Get finished matches from ESPN using mass concurrency with Semaphore.
        """
        matches = []
        leagues_to_fetch = league_codes or list(ESPN_LEAGUE_MAPPING.keys())

        # Determine date range
        if start_date and end_date:
            date_range = []
            curr = start_date
            while curr <= end_date:
                date_range.append(curr.strftime("%Y%m%d"))
                curr += timedelta(days=1)
        elif days_back:
            date_range = [
                (datetime.utcnow() - timedelta(days=i)).strftime("%Y%m%d")
                for i in range(days_back)
            ]
        else:
            date_range = [
                (datetime.utcnow() - timedelta(days=i)).strftime("%Y%m%d")
                for i in range(7)
            ]

        semaphore = asyncio.Semaphore(10)  # Rate limit concurrency

        async def fetch_scoreboard(code: str, date_str: str):
            slug = ESPN_LEAGUE_MAPPING.get(code)
            if not slug:
                return []
            async with semaphore:
                url = f"{self.BASE_URL}/{slug}/scoreboard"
                data = await self._make_request(url, {"dates": date_str})

            if not data or "events" not in data:
                return []

            event_tasks = []
            for event in data["events"]:
                status = event.get("status", {}).get("type", {}).get("state")
                if status == "post":
                    match_id = event.get("id")
                    event_tasks.append(
                        self._get_match_details_atomic(
                            slug, match_id, event, code, semaphore
                        )
                    )

            return await asyncio.gather(*event_tasks)

        # 1. Parallel Scoreboard Fetching
        tasks = []
        for code in leagues_to_fetch:
            for date_str in date_range:
                tasks.append(fetch_scoreboard(code, date_str))

        logger.info(
            f"ESPN: Fetching history for {len(leagues_to_fetch)} leagues across {len(date_range)} days..."
        )
        results = await asyncio.gather(*tasks)

        # Flatten results
        for day_results in results:
            for match in day_results:
                if match:
                    matches.append(match)

        logger.info(f"ESPN: fetched {len(matches)} matches total")
        return matches

    async def _get_match_details_atomic(
        self,
        slug: str,
        match_id: str,
        event_summary: dict,
        league_code: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Match]:
        """Atomic helper for concurrent match details fetching."""
        async with semaphore:
            return await self._get_match_details(
                slug, match_id, event_summary, league_code
            )

    async def _get_match_details(
        self, slug: str, match_id: str, event_summary: dict, league_code: str
    ) -> Optional[Match]:
        """Fetch details (summary) to get stats."""
        url = f"{self.BASE_URL}/{slug}/summary"
        data = await self._make_request(url, {"event": match_id})

        if not data:
            # Fallback to scoreboard data only (no stats)
            return self._parse_scoreboard_match(event_summary, league_code)

        # Parse detailed stats from boxscore
        boxscore = data.get("boxscore", {})
        teams = boxscore.get("teams", [])

        home_team_stats = {}
        away_team_stats = {}

        # Determine home/away from rosters
        rosters = data.get("rosters", [])
        home_team_id = None
        away_team_id = None
        for roster in rosters:
            if roster.get("homeAway") == "home":
                home_team_id = roster.get("team", {}).get("id")
            else:
                away_team_id = roster.get("team", {}).get("id")

        for team_data in teams:
            tid = team_data.get("team", {}).get("id")
            stats = {
                s["name"]: s["displayValue"] for s in team_data.get("statistics", [])
            }

            if tid == home_team_id:
                home_team_stats = stats
            elif tid == away_team_id:
                away_team_stats = stats

        # Extract odds
        odds = None
        pickcenter = data.get("pickcenter", [])
        if pickcenter:
            pick = pickcenter[0]
            home_odds_data = pick.get("homeTeamOdds", {})
            away_odds_data = pick.get("awayTeamOdds", {})
            odds = ESPNOdds(
                home_odds=home_odds_data.get("moneyLine")
                or home_odds_data.get("value"),
                draw_odds=(
                    pick.get("drawOdds", {}).get("value")
                    if pick.get("drawOdds")
                    else None
                ),
                away_odds=away_odds_data.get("moneyLine")
                or away_odds_data.get("value"),
            )

        return self._parse_full_match(
            event_summary, home_team_stats, away_team_stats, league_code, odds
        )

    def _parse_scoreboard_match(self, event: dict, league_code: str) -> Optional[Match]:
        """Parse match from scoreboard without extra stats."""
        # TODO: Implement basic parsing
        return None  # For now only return detailed matches

    def _parse_full_match(
        self,
        event: dict,
        home_stats: dict,
        away_stats: dict,
        league_code: str,
        odds: Optional[ESPNOdds] = None,
    ) -> Optional[Match]:
        try:
            competition = event["competitions"][0]
            competitors = competition["competitors"]
            home_comp = competitors[0]
            away_comp = competitors[1]

            # Ensure home is really home
            if home_comp["homeAway"] != "home":
                home_comp, away_comp = away_comp, home_comp
                home_stats, away_stats = away_stats, home_stats

            # Date
            date_str = event.get("date")  # "2024-12-01T13:30Z"
            match_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ").replace(
                tzinfo=timezone.utc
            )

            # Teams with logos from TeamService
            home_name = home_comp["team"]["displayName"]
            away_name = away_comp["team"]["displayName"]

            home_team = Team(
                id=home_comp["team"]["id"],
                name=home_name,
                logo_url=(
                    TeamService.get_team_logo(home_name)
                    or home_comp["team"].get("logo")
                ),
            )
            away_team = Team(
                id=away_comp["team"]["id"],
                name=away_name,
                logo_url=(
                    TeamService.get_team_logo(away_name)
                    or away_comp["team"].get("logo")
                ),
            )

            # Score
            home_goals = int(home_comp["score"])
            away_goals = int(away_comp["score"])

            # Stats (parse strings to ints)
            def p_int(val):
                try:
                    return int(float(val)) if val else None
                except Exception:
                    return None

            return Match(
                id=f"espn_{event['id']}",
                home_team=home_team,
                away_team=away_team,
                league=League(
                    id=league_code,
                    name=ESPN_LEAGUE_MAPPING[league_code],
                    country="Europe",
                ),
                match_date=match_date,
                home_goals=home_goals,
                away_goals=away_goals,
                status="FT",
                # Basic Stats
                home_corners=p_int(home_stats.get("wonCorners")),
                away_corners=p_int(away_stats.get("wonCorners")),
                home_yellow_cards=p_int(home_stats.get("yellowCards")),
                away_yellow_cards=p_int(away_stats.get("yellowCards")),
                home_red_cards=p_int(home_stats.get("redCards")),
                away_red_cards=p_int(away_stats.get("redCards")),
                # Advanced Stats
                home_total_shots=p_int(home_stats.get("totalShots")),
                away_total_shots=p_int(away_stats.get("totalShots")),
                home_shots_on_target=p_int(home_stats.get("shotsOnTarget")),
                away_shots_on_target=p_int(away_stats.get("shotsOnTarget")),
                home_possession=home_stats.get("possessionPct"),
                away_possession=away_stats.get("possessionPct"),
                home_fouls=p_int(home_stats.get("foulsCommitted")),
                away_fouls=p_int(away_stats.get("foulsCommitted")),
                # Odds from ESPN (if available)
                home_odds=odds.home_odds if odds else None,
                draw_odds=odds.draw_odds if odds else None,
                away_odds=odds.away_odds if odds else None,
            )

        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    def _convert_odds(self, american_odds: str) -> Optional[float]:
        """
        Convert American odds (e.g., "+120", "-150") to Decimal odds.
        Returns rounded to 2 decimal places.
        """
        try:
            val = int(american_odds)
            if val > 0:
                decimal = (val / 100) + 1
            else:
                decimal = (100 / abs(val)) + 1
            return round(decimal, 2)
        except (ValueError, TypeError):
            return None

    async def get_upcoming_matches(
        self, league_code: str, days_ahead: int = 7
    ) -> List[Match]:
        """
        Get upcoming matches for a league with odds in parallel.
        """
        matches = []
        slug = ESPN_LEAGUE_MAPPING.get(league_code)
        if not slug:
            return []

        # Get dates for upcoming days
        dates_to_fetch = []
        now = datetime.utcnow()
        for i in range(days_ahead + 1):
            d = now + timedelta(days=i)
            dates_to_fetch.append(d.strftime("%Y%m%d"))

        semaphore = asyncio.Semaphore(5)

        async def fetch_day_upcoming(date_str: str):
            url = f"{self.BASE_URL}/{slug}/scoreboard"
            async with semaphore:
                data = await self._make_request(url, {"dates": date_str})

            if not data or "events" not in data:
                return []

            match_tasks = []
            for event in data["events"]:
                status = event.get("status", {}).get("type", {}).get("state")
                if status in ["pre"]:
                    match_id = event.get("id")
                    match_tasks.append(
                        self._fetch_upcoming_match_details(
                            slug, match_id, event, league_code, semaphore
                        )
                    )

            return await asyncio.gather(*match_tasks)

        results = await asyncio.gather(*[fetch_day_upcoming(d) for d in dates_to_fetch])

        for day_matches in results:
            for m in day_matches:
                if m:
                    matches.append(m)

        return matches

    async def _fetch_upcoming_match_details(
        self,
        slug: str,
        match_id: str,
        event: dict,
        league_code: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Match]:
        """Fetch summary to get Odds (pickcenter) in parallel."""
        async with semaphore:
            summary = await self._make_request(
                f"{self.BASE_URL}/{slug}/summary", {"event": match_id}
            )
            if not summary:
                return None
            return self._parse_upcoming_match(event, summary, league_code)

    def _parse_upcoming_match(
        self, event: dict, summary: dict, league_code: str
    ) -> Optional[Match]:
        """Parse upcoming match data including odds."""
        try:
            competition = event["competitions"][0]
            competitors = competition["competitors"]
            home_comp = competitors[0]
            away_comp = competitors[1]

            # Ensure home is really home
            if home_comp["homeAway"] != "home":
                home_comp, away_comp = away_comp, home_comp

            # Date
            date_str = event.get("date")
            match_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ").replace(
                tzinfo=timezone.utc
            )

            # Teams
            home_name = home_comp["team"]["displayName"]
            away_name = away_comp["team"]["displayName"]

            home_logo = TeamService.get_team_logo(home_name) or home_comp["team"].get(
                "logo"
            )
            home_team = Team(
                id=home_comp["team"]["id"],
                name=home_name,
                logo_url=home_logo,
            )
            away_logo = TeamService.get_team_logo(away_name) or away_comp["team"].get(
                "logo"
            )
            away_team = Team(
                id=away_comp["team"]["id"],
                name=away_name,
                logo_url=away_logo,
            )

            # Odds Parsing
            home_odds = None
            draw_odds = None
            away_odds = None

            pickcenter = summary.get("pickcenter", [])

            if pickcenter:
                # Prioritize provider if needed, currently taking first that has data
                for pick in pickcenter:
                    # Look for moneyline or 3-way
                    # ESPN structure: provider->homeTeamOdds->moneyLine (e.g. '+140')

                    h_data = pick.get("homeTeamOdds", {})
                    a_data = pick.get("awayTeamOdds", {})
                    d_data = pick.get("drawOdds", {})

                    h_val = h_data.get("moneyLine")
                    a_val = a_data.get("moneyLine")
                    d_val = d_data.get("moneyLine")

                    if h_val and a_val:
                        home_odds = self._convert_odds(str(h_val))
                        away_odds = self._convert_odds(str(a_val))
                        draw_odds = self._convert_odds(str(d_val)) if d_val else None

                        if home_odds and away_odds:
                            break  # Found valid odds

            return Match(
                id=f"espn_{event['id']}",
                home_team=home_team,
                away_team=away_team,
                league=League(
                    id=league_code,
                    name=ESPN_LEAGUE_MAPPING[league_code],
                    country="Europe",
                ),
                match_date=match_date,
                status="NS",  # Not Started
                # Odds
                home_odds=home_odds,
                draw_odds=draw_odds,
                away_odds=away_odds,
            )

        except Exception as e:
            logger.debug(f"Error parsing upcoming ESPN match: {e}")
            return None
