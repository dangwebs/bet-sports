import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from src.infrastructure.data_sources.espn import ESPNSource

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    espn = ESPNSource()
    
    logger.info("Calling get_upcoming_matches('SP1', days_ahead=7)...")
    matches = await espn.get_upcoming_matches("SP1", days_ahead=7)
    
    if not matches:
        logger.warning("No matches returned from get_upcoming_matches!")
        return

    logger.info(f"Found {len(matches)} matches.")
    
    odds_count = 0
    for m in matches:
        has_odds = m.home_odds or m.away_odds
        logger.info(f"Match: {m.home_team.name} vs {m.away_team.name} ({m.match_date})")
        logger.info(f"  Odds: Home={m.home_odds}, Draw={m.draw_odds}, Away={m.away_odds}")
        if has_odds:
            odds_count += 1
            
    logger.info(f"Total matches with odds: {odds_count}/{len(matches)}")

if __name__ == "__main__":
    asyncio.run(main())
