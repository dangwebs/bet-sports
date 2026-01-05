
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
    
    try:
        session = repo.db_service.get_session()
        count = session.execute(text("SELECT count(*) FROM match_predictions")).scalar()
        logger.info(f"Total rows in 'match_predictions': {count}")
        
        # Check Manchester City Stats from TrainingResult (JSON)
        logger.info("Checking 'latest_daily' training result for Man City stats...")
        # Use query text specific to the table structure shown in repository
        res = session.execute(text("SELECT data FROM training_results WHERE key = 'latest_daily'")).first()
        
        if res and res[0]:
            import json
            data = res[0]
            if isinstance(data, str): data = json.loads(data)
            
            team_stats = data.get('team_stats', {})
            man_city = team_stats.get('Manchester City')
            
            if man_city:
                logger.info(f"Man City Stats: Matches Played={man_city.get('matches_played')}, Goals Scored={man_city.get('goals_scored')}")
            else:
                logger.info("Man City stats not found in 'latest_daily' (Keys checked: Manchester City)")
        else:
            logger.info("'latest_daily' training result not found")
            
    except Exception as e:
        logger.error(f"Error accessing DB: {e}", exc_info=True)

        
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
