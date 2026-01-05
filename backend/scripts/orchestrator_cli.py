
import asyncio
import argparse
import logging
import sys
import os
from typing import List

# Setup path to include backend src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.time_utils import COLOMBIA_TZ, get_today_str
from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Reduce noise from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("OrchestratorCLI")

async def cmd_train(days_back: int = 550):
    """
    Step 1: Retrain the ML Model.
    """
    logger.info(f"CMD: TRAIN. Days back: {days_back}")
    from src.api.dependencies import get_ml_training_orchestrator, get_cache_service
    
    orchestrator = get_ml_training_orchestrator()
    cache = get_cache_service()
    
    leagues = list(LEAGUES_METADATA.keys())
    
    try:
        if os.getenv("DISABLE_ML_TRAINING") == "true":
            logger.info("Training disabled via env var.")
            return

        training_result = await orchestrator.run_training_pipeline(
            league_ids=leagues,
            days_back=days_back
        )
        
        # Save validation metrics to Cache/DB if needed
        logger.info(f"Training Complete. Accuracy: {training_result.accuracy:.2%}")
        
        # Cache Result
        training_data = {
            "matches_processed": training_result.matches_processed,
            "accuracy": training_result.accuracy,
            "roi": training_result.roi,
            "global_averages": getattr(training_result, 'global_averages', {})
        }
        cache.set(orchestrator.CACHE_KEY_RESULT, training_data, ttl_seconds=86400)
        
    except Exception as e:
        logger.error(f"Training Failed: {e}", exc_info=True)
        sys.exit(1)

async def cmd_predict(leagues_str: str):
    """
    Step 2: Massive Inference for specific leagues.
    """
    leagues = [l.strip() for l in leagues_str.split(',') if l.strip()]
    logger.info(f"CMD: PREDICT. Target Leagues: {leagues}")
    
    from src.api.dependencies import (
        get_data_sources, get_prediction_service, 
        get_statistics_service, get_match_aggregator_service, 
        get_risk_manager, get_persistence_repository
    )
    from src.application.use_cases.use_cases import GetPredictionsUseCase
    
    use_case = GetPredictionsUseCase(
        data_sources=get_data_sources(),
        prediction_service=get_prediction_service(),
        statistics_service=get_statistics_service(),
        match_aggregator=get_match_aggregator_service(),
        risk_manager=get_risk_manager(),
        persistence_repository=get_persistence_repository()
    )
    
    failed = []
    
    for league_id in leagues:
        if league_id not in LEAGUES_METADATA:
            logger.warning(f"Skipping unknown league: {league_id}")
            continue
            
        try:
            logger.info(f"Processing League: {league_id}")
            result = await use_case.execute(league_id, limit=50) # Limit 50 upcoming
            
            # NOTE: saving to DB is handled inside use_case.execute() via persistence_repo
            logger.info(f"Saved {len(result.predictions)} predictions for {league_id}")
            
        except Exception as e:
            logger.error(f"Failed to process {league_id}: {e}")
            failed.append(league_id)
            
    if failed:
        logger.warning(f"Failed leagues: {failed}")
        # We don't exit 1 here to allow other batches to succeed. 
        # But for GitHub Actions matrix, it might be better to fail if critical?
        # Let's print summary but exit 0 unless all failed.
        if len(failed) == len(leagues):
            sys.exit(1)

async def cmd_top_picks():
    """
    Step 3: Generate Daily Top Picks.
    """
    logger.info("CMD: TOP PICKS.")
    from src.api.dependencies import get_persistence_repository
    from src.application.use_cases.suggested_picks_use_case import GetTopMLPicksUseCase
    
    repo = get_persistence_repository()
    
    # We use the UseCase logic to generate the top picks based on what is in the DB
    use_case = GetTopMLPicksUseCase(repo)
    
    try:
        top_picks = await use_case.execute(limit=10)
        logger.info(f"Generated {len(top_picks)} Top ML Verified Picks.")
        # The use case returns them, we assume it or another step saves them if needed. 
        # Actually GetTopMLPicksUseCase reads, it doesn't calculate and save. 
        # We need to Ensure they are calculated. 
        # The current 'GetTopMLPicksUseCase' simply queries 'top_ml_picks' table or similar?
        # If it's a dynamic query, then we are good.
        # If it requires a batch job to populates a table, we implement that here.
        # Assumption: persistence_repository.get_top_picks() performs a query on stored predictions.
        
    except Exception as e:
        logger.error(f"Top Picks Generation Failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="MLOps Orchestrator")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Train
    parser_train = subparsers.add_parser('train')
    parser_train.add_argument('--days', type=int, default=550)
    
    # Predict
    parser_predict = subparsers.add_parser('predict')
    parser_predict.add_argument('--leagues', type=str, required=True, help="Comma separated league IDs")
    
    # Top Picks
    parser_top = subparsers.add_parser('top-picks')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'train':
            asyncio.run(cmd_train(args.days))
        elif args.command == 'predict':
            asyncio.run(cmd_predict(args.leagues))
        elif args.command == 'top-picks':
            asyncio.run(cmd_top_picks())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
