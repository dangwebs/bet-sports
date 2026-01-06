import asyncio
import argparse
import logging
import sys
import os
from typing import List
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

# Load environment variables from .env file FIRST
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Setup path to include backend src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.time_utils import COLOMBIA_TZ, get_today_str
from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
from src.core.constants import DEFAULT_LEAGUES

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Reduce noise from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("OrchestratorCLI")

# Detectar número de CPUs disponibles
CPU_COUNT = int(os.getenv('N_JOBS', multiprocessing.cpu_count()))
logger.info(f"🚀 Running with {CPU_COUNT} CPU cores")

async def cmd_train(days_back: int = 550, n_jobs: int = None):
    """
    Step 1: Retrain the ML Model with parallel processing.
    """
    if n_jobs is None:
        n_jobs = CPU_COUNT
        
    logger.info(f"CMD: TRAIN. Days back: {days_back}, n_jobs: {n_jobs}")
    from src.api.dependencies import get_ml_training_orchestrator, get_cache_service
    
    orchestrator = get_ml_training_orchestrator()
    cache = get_cache_service()
    
    # [FIX] Get Persistence Repo to save results to DB (source of truth for Dashboard)
    from src.api.dependencies import get_persistence_repository
    repo = get_persistence_repository()
    
    # Use DEFAULT_LEAGUES (Top Tier Only) instead of all metadata
    leagues = DEFAULT_LEAGUES
    logger.info(f"Targeting Leagues: {leagues}")
    
    try:
        if os.getenv("DISABLE_ML_TRAINING") == "true":
            logger.info("Training disabled via env var.")
            return

        # Pasar n_jobs al orchestrator si lo soporta
        # Si tu orchestrator no soporta n_jobs, necesitarás modificarlo
        training_result = await orchestrator.run_training_pipeline(
            league_ids=leagues,
            days_back=days_back,
            n_jobs=n_jobs  # Añade este parámetro si tu orchestrator lo soporta
        )
        
        # Save validation metrics to Cache/DB if needed
        logger.info(f"✅ Training Complete. Accuracy: {training_result.accuracy:.2%}")
        
        # Cache Result
        training_data = {
            "matches_processed": training_result.matches_processed,
            "accuracy": training_result.accuracy,
            "roi": training_result.roi,
            "global_averages": getattr(training_result, 'global_averages', {})
        }
        cache.set(orchestrator.CACHE_KEY_RESULT, training_data, ttl_seconds=86400)
        
        # [FIX] Persist to Database for Dashboard Visibility
        # This allows the API to serve this data even after the GitHub Action runner dies
        logger.info("💾 Persisting Training Result to Database...")
        repo.save_training_result("latest_daily", training_result.model_dump())
        logger.info("✅ Training Result successfully saved to DB (key: latest_daily)")
        
    except Exception as e:
        logger.error(f"❌ Training Failed: {e}", exc_info=True)
        sys.exit(1)

async def process_league_async(league_id: str, use_case):
    """
    Helper para procesar una liga de manera asíncrona.
    """
    if league_id not in LEAGUES_METADATA:
        logger.warning(f"⚠️  Skipping unknown league: {league_id}")
        return None
    
    try:
        logger.info(f"🔄 Processing League: {league_id}")
        result = await use_case.execute(league_id, limit=50)
        logger.info(f"✅ Saved {len(result.predictions)} predictions for {league_id}")
        return league_id, True
    except Exception as e:
        logger.error(f"❌ Failed to process {league_id}: {e}")
        return league_id, False

async def cmd_predict(leagues_str: str, parallel: bool = True):
    """
    Step 2: Massive Inference for specific leagues with parallel processing.
    """
    leagues = [l.strip() for l in leagues_str.split(',') if l.strip()]
    logger.info(f"CMD: PREDICT. Target Leagues: {leagues}, Parallel: {parallel}")
    
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
    
    if parallel and len(leagues) > 1:
        # Procesar múltiples ligas en paralelo usando asyncio.gather
        logger.info(f"🔥 Processing {len(leagues)} leagues in parallel")
        tasks = [process_league_async(league_id, use_case) for league_id in leagues]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analizar resultados
        failed = []
        succeeded = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception during processing: {result}")
                failed.append("unknown")
            elif result and result[1]:
                succeeded.append(result[0])
            elif result:
                failed.append(result[0])
        
        logger.info(f"📊 Results: ✅ {len(succeeded)} succeeded, ❌ {len(failed)} failed")
        
        if failed:
            logger.warning(f"⚠️  Failed leagues: {failed}")
            if len(failed) == len(leagues):
                logger.error("❌ All leagues failed!")
                sys.exit(1)
    else:
        # Procesamiento secuencial (fallback)
        logger.info(f"🔄 Processing {len(leagues)} leagues sequentially")
        failed = []
        for league_id in leagues:
            result = await process_league_async(league_id, use_case)
            if result and not result[1]:
                failed.append(result[0])
        
        if failed and len(failed) == len(leagues):
            logger.error("❌ All leagues failed!")
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
        if top_picks and top_picks.picks:
            logger.info(f"✅ Generated {len(top_picks.picks)} Top ML Verified Picks.")
            
            # [FIX] Persist Top Picks to Database
            logger.info("💾 Persisting Top Picks to Database...")
            repo.save_training_result("top_ml_picks", top_picks.model_dump())
            logger.info("✅ Top Picks successfully saved to DB (key: top_ml_picks)")
        else:
            logger.info("ℹ️ No Top Picks generated.")
        
    except Exception as e:
        logger.error(f"❌ Top Picks Generation Failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="MLOps Orchestrator - Optimized for Parallel Processing")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Train
    parser_train = subparsers.add_parser('train', help='Train ML model')
    parser_train.add_argument('--days', type=int, default=550,
                              help='Number of days back for training data (default: 550)')
    parser_train.add_argument('--n-jobs', type=int, default=None, 
                              help='Number of parallel jobs for ML training (default: auto-detect)')
    
    # Predict
    parser_predict = subparsers.add_parser('predict', help='Run predictions for leagues')
    parser_predict.add_argument('--leagues', type=str, required=True, 
                                help="Comma separated league IDs (e.g., 'E0,E1,E2')")
    parser_predict.add_argument('--parallel', action='store_true', default=True,
                                help='Process leagues in parallel (default: True)')
    parser_predict.add_argument('--sequential', dest='parallel', action='store_false',
                                help='Process leagues sequentially')
    
    # Top Picks
    parser_top = subparsers.add_parser('top-picks', help='Generate top ML picks')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'train':
            asyncio.run(cmd_train(args.days, args.n_jobs))
        elif args.command == 'predict':
            asyncio.run(cmd_predict(args.leagues, args.parallel))
        elif args.command == 'top-picks':
            asyncio.run(cmd_top_picks())
    except KeyboardInterrupt:
        logger.info("⚠️  Interrupted by user")
        pass
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()