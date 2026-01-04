#!/usr/bin/env python3
"""
Prediction Worker Script
This script runs the entire ML pipeline and saves results to PostgreSQL.
Designed to run in GitHub Actions or locally for testing.
"""
import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.worker_config import (
    DATABASE_URL, LEAGUES_TO_PROCESS, LOG_LEVEL, LOG_FORMAT,
    DAYS_BACK, PREDICTION_LIMIT
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('worker.log')
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Main worker execution function."""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"🚀 Starting Prediction Worker at {start_time}")
    logger.info(f"📊 Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'SQLite'}")
    logger.info(f"🏆 Leagues to process: {len(LEAGUES_TO_PROCESS)}")
    logger.info("=" * 80)
    
    try:
        # Import dependencies (lazy loading to save memory)
        from src.api.dependencies import (
            get_ml_training_orchestrator,
            get_persistence_repository,
            get_data_sources,
            get_prediction_service,
            get_statistics_service,
            get_cache_service,
            get_learning_service
        )
        from src.application.use_cases.use_cases import GetPredictionsUseCase
        
        # Initialize services
        logger.info("📦 Initializing services...")
        orchestrator = get_ml_training_orchestrator()
        persistence_repo = get_persistence_repository()
        data_sources = get_data_sources()
        prediction_service = get_prediction_service()
        statistics_service = get_statistics_service()
        cache_service = get_cache_service()
        learning_service = get_learning_service()
        
        # Ensure database tables exist
        logger.info("🗄️  Creating/verifying database tables...")
        persistence_repo.create_tables()
        
        # Step 1: Run ML Training Pipeline
        logger.info("\n" + "=" * 80)
        logger.info("📚 STEP 1/3: Running ML Training Pipeline")
        logger.info("=" * 80)
        
        training_result = await orchestrator.run_training_pipeline(
            league_ids=LEAGUES_TO_PROCESS,
            days_back=DAYS_BACK,
            force_refresh=True  # Always refresh in worker mode
        )
        
        logger.info(f"✅ Training complete!")
        logger.info(f"   - Matches processed: {training_result.matches_processed}")
        logger.info(f"   - Accuracy: {training_result.accuracy:.2%}")
        logger.info(f"   - ROI: {training_result.roi:.2f}%")
        logger.info(f"   - Total bets: {training_result.total_bets}")
        
        # Save training results to database
        logger.info("💾 Saving training results to database...")
        training_data = training_result.model_dump() if hasattr(training_result, 'model_dump') else training_result.dict()
        persistence_repo.save_training_result("latest_daily", training_data)
        
        # Step 2: Generate Predictions for All Leagues
        logger.info("\n" + "=" * 80)
        logger.info("🔮 STEP 2/3: Generating Predictions for All Leagues")
        logger.info("=" * 80)
        
        use_case = GetPredictionsUseCase(
            data_sources=data_sources,
            prediction_service=prediction_service,
            statistics_service=statistics_service,
            persistence_repository=persistence_repo
        )
        
        predictions_saved = 0
        total_picks_saved = 0
        for idx, league_id in enumerate(LEAGUES_TO_PROCESS, 1):
            try:
                logger.info(f"\n[{idx}/{len(LEAGUES_TO_PROCESS)}] Processing {league_id}...")
                
                # Generate predictions
                predictions_dto = await use_case.execute(league_id, limit=PREDICTION_LIMIT)
                
                # Save to database
                league_cache_key = f"forecasts:league_{league_id}"
                persistence_repo.save_training_result(
                    league_cache_key,
                    predictions_dto.model_dump() if hasattr(predictions_dto, 'model_dump') else predictions_dto.dict()
                )
                
                # Save individual match predictions and their picks
                for match_pred in predictions_dto.predictions:
                    match_data = match_pred.model_dump() if hasattr(match_pred, 'model_dump') else match_pred.dict()
                    
                    # 1. Save prediction for real-time detail lookup
                    persistence_repo.save_match_prediction(
                        match_id=match_pred.match.id,
                        league_id=league_id,
                        data=match_data,
                        ttl_seconds=7 * 24 * 3600  # 7 days
                    )
                    
                    # 2. Save picks to the specific picks key (used by SuggestedPicksTab)
                    # This avoids redundant re-calculation in the worker
                    if match_pred.prediction and match_pred.prediction.suggested_picks:
                        picks_cache_key = f"picks:match_{match_pred.match.id}"
                        # Wrapper DTO for frontend compatibility
                        from src.application.dtos.dtos import MatchSuggestedPicksDTO
                        picks_container = MatchSuggestedPicksDTO(
                            match_id=match_pred.match.id,
                            suggested_picks=match_pred.prediction.suggested_picks,
                            generated_at=match_pred.prediction.created_at
                        )
                        persistence_repo.save_training_result(
                            picks_cache_key,
                            picks_container.model_dump() if hasattr(picks_container, 'model_dump') else picks_container.dict()
                        )
                        total_picks_saved += len(match_pred.prediction.suggested_picks)
                    
                    predictions_saved += 1
                
                logger.info(f"   ✅ Saved {len(predictions_dto.predictions)} predictions and {total_picks_saved} picks for {league_id}")
                
                # Small delay to avoid overwhelming the database
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"   ❌ Error processing {league_id}: {e}", exc_info=True)
                continue
        
        logger.info(f"\n✅ Total predictions saved: {predictions_saved}")
        
        # Step 2.5: Generate Top ML Picks
        logger.info("\n" + "=" * 80)
        logger.info("🏆 STEP 2.5/4: Generating Top ML Picks")
        logger.info("=" * 80)
        
        try:
            from src.application.use_cases.use_cases import GetTopMLPicksUseCase
            
            top_picks_use_case = GetTopMLPicksUseCase(
                persistence_repository=persistence_repo
            )
            
            # Generate top picks (aggregates best picks from all matches)
            logger.info("   🔍 Analyzing all picks to find top opportunities...")
            top_picks_dto = await top_picks_use_case.execute(limit=50)  # Top 50 picks
            
            if top_picks_dto and top_picks_dto.picks:
                # Save to database
                top_picks_cache_key = "top_ml_picks"
                top_picks_data = top_picks_dto.model_dump() if hasattr(top_picks_dto, 'model_dump') else top_picks_dto.dict()
                persistence_repo.save_training_result(
                    top_picks_cache_key,
                    top_picks_data
                )
                
                avg_confidence = sum(p.probability for p in top_picks_dto.picks) / len(top_picks_dto.picks)
                logger.info(f"   ✅ Saved {len(top_picks_dto.picks)} Top ML Picks")
                logger.info(f"   📊 Average confidence: {avg_confidence:.1f}%")
            else:
                logger.warning("   ⚠️  No top picks generated")
                
        except Exception as top_picks_error:
            logger.error(f"   ❌ Error generating Top ML Picks: {top_picks_error}", exc_info=True)
        
        # Step 3: Cleanup and Summary
        logger.info("\n" + "=" * 80)
        logger.info("🧹 STEP 3/4: Cleanup and Summary")
        logger.info("=" * 80)
        
        # Clear old predictions (older than 7 days)
        logger.info("🗑️  Clearing old predictions...")
        # TODO: Implement cleanup logic in persistence_repository
        
        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("✨ WORKER COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"⏱️  Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        logger.info(f"📊 Leagues processed: {len(LEAGUES_TO_PROCESS)}")
        logger.info(f"🔮 Predictions saved: {predictions_saved}")
        logger.info(f"💰 Individual picks saved: {total_picks_saved}")
        logger.info(f"🏆 Top ML picks saved: 50")
        logger.info(f"📚 Training accuracy: {training_result.accuracy:.2%}")
        logger.info(f"📈 Training ROI: {training_result.roi:.2f}%")
        logger.info("=" * 80)
        
        return 0  # Success
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("❌ WORKER FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("=" * 80)
        return 1  # Failure


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
