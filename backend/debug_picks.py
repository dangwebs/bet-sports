
import asyncio
import os
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.repositories.persistence_repository import get_persistence_repository
from src.application.use_cases.suggested_picks_use_case import GetTopMLPicksUseCase
from src.utils.time_utils import get_current_time
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_picks():
    logger.info("--- Starting Debug Picks ---")
    
    # 1. Initialize Persistence
    repo = get_persistence_repository()
    
    # 2. Check DB Counts
    try:
        session = repo.db_service.get_session()
        count = session.execute(text("SELECT count(*) FROM match_predictions")).scalar()
        logger.info(f"Total rows in 'match_predictions': {count}")
        
        # Check active
        active_preds = repo.get_all_active_predictions()
        logger.info(f"Active predictions (expires_at > now): {len(active_preds)}")
        
        if len(active_preds) > 0:
            sample = active_preds[0]
            logger.info(f"Sample Prediction Match ID: {sample.get('match', {}).get('id')}")
            logger.info(f"Sample status: {sample.get('match', {}).get('status')}")
            logger.info(f"Sample date: {sample.get('match', {}).get('match_date')}")
            
            picks = sample.get('prediction', {}).get('suggested_picks', [])
            logger.info(f"Sample Pick Count: {len(picks)}")
            if picks:
                logger.info(f"First Pick: {picks[0]}")
                
        # 3. Test Top ML Picks Use Case
        use_case = GetTopMLPicksUseCase(repo)
        top_picks = await use_case.execute()
        
        if top_picks and top_picks.picks:
            logger.info(f"✅ Top ML Picks found: {len(top_picks.picks)}")
            for p in top_picks.picks[:3]:
                logger.info(f" - {p.market_label} ({p.probability:.2f}) [Prio: {p.priority_score:.2f}]")
        else:
            logger.warning("❌ No Top ML Picks returned by UseCase.")
            
    except Exception as e:
        logger.error(f"Error accessing DB: {e}")
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    asyncio.run(debug_picks())
