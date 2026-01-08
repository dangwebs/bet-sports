import asyncio
import os
import sys
import gc
import logging
import time
from typing import List, Tuple, Any, Dict
from datetime import datetime
import joblib
import numpy as np

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrainPerLeague")

# Import Services
from src.infrastructure.database.database_service import get_database_service
from src.infrastructure.cache.cache_service import get_cache_service
from src.application.services.training_data_service import TrainingDataService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.picks_service import PicksService
from src.domain.services.learning_service import LearningService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.pick_resolution_service import PickResolutionService
from src.core.constants import DEFAULT_LEAGUES

# Global Service Instances (for worker processes)
_prediction_service = None
_picks_service = None
_statistics_service = None
_feature_extractor = None
_resolution_service = None

def init_worker(weights):
    """Initialize services in the worker process"""
    global _prediction_service, _picks_service, _statistics_service, _feature_extractor, _resolution_service
    
    _statistics_service = StatisticsService()
    _prediction_service = PredictionService() # learning_service not needed for pure prediction generation?
    # Actually PredictionService might need simple init.
    
    _picks_service = PicksService(learning_weights=weights)
    _feature_extractor = MLFeatureExtractor()
    _resolution_service = PickResolutionService()

def process_match_task(task_data):
    """
    Pure function to process a single match task.
    Args:
        task_data: tuple(match, home_stats_dict, away_stats_dict, league_avgs, global_avgs, learning_weights)
    
    Returns:
        tuple: (features, targets_dict)
    """
    global _prediction_service, _picks_service, _statistics_service, _feature_extractor, _resolution_service
    
    match, raw_home, raw_away, league_avgs, global_avgs, weights = task_data
    
    # Lazy Init in Worker Process
    if _statistics_service is None:
        init_worker(weights)
    
    # 1. Convert to Domain Stats (Fast)
    home_stats = _statistics_service.convert_to_domain_stats(match.home_team.name, raw_home)
    away_stats = _statistics_service.convert_to_domain_stats(match.away_team.name, raw_away)
    
    # 2. Extract Features (Now includes Variance/Rolling stats)
    # We create a dummy pick to satisfy the signature or adjust the extractor.
    # The extractor takes a 'pick', but really only needs market type for hash.
    # Let's create a generic feature vector.
    from src.domain.entities.suggested_pick import SuggestedPick
    
    # We need a base 'pick' object to extract features. 
    # Since we are training for GENERAL match stats (Corners, Cards), 
    # we can use a dummy pick or modify extract_features. 
    # For now, let's assume we are training the Match Outcome mostly, 
    # but for Regressors (Corners), the "pick" features (prob, ev) don't matter as much 
    # as the team stats features.
    
    dummy_pick = SuggestedPick(
        match_id=match.id,
        market_type="MATCH_WINNER", # Generic
        selection="HOME",
        probability=0.5,
        odds=2.0,
        stake=1.0,
        expected_value=0.0,
        risk_level=1.0,
        reason="Training"
    )
    
    features = _feature_extractor.extract_features(dummy_pick, match, home_stats, away_stats)
    
    # 3. Define Targets for Regression & Classification
    targets = {
        "home_win": 1 if match.home_goals > match.away_goals else 0,
        "away_win": 1 if match.away_goals > match.home_goals else 0,
        "draw": 1 if match.home_goals == match.away_goals else 0,
        "total_corners": (match.home_corners or 0) + (match.away_corners or 0),
        "total_cards": (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0),
        "home_goals": match.home_goals,
        "away_goals": match.away_goals
    }
    
    return features, targets

async def main():
    logger.info("🚀 Starting Per-League ML Training Pipeline...")
    start_time = time.time()
    
    # --- 1. SETUP ---
    from src.api.dependencies import get_training_data_service, get_statistics_service
    training_service = get_training_data_service()
    stats_service = get_statistics_service()
    learning_service = LearningService()
    
    # Ensure models directory exists
    os.makedirs("ml_models", exist_ok=True)
    
    # Fetch Data
    logger.info("📥 Fetching Training Data (550 days)...")
    matches = await training_service.fetch_comprehensive_training_data(
        leagues=DEFAULT_LEAGUES,
        days_back=550,
        force_refresh=False
    )
    logger.info(f"✅ Loaded {len(matches)} matches.")
    
    # Sort Chronologically
    matches.sort(key=lambda x: x.match_date.replace(tzinfo=None))
    
    # Group by League
    matches_by_league = {}
    for m in matches:
        matches_by_league.setdefault(m.league.id, []).append(m)
        
    # --- 2. TRAIN PER LEAGUE ---
    
    for league_id, league_matches in matches_by_league.items():
        if len(league_matches) < 50:
            logger.warning(f"⚠️ Skipping league {league_id}: Not enough data ({len(league_matches)} matches)")
            continue
            
        logger.info(f"🏟️ Processing League: {league_id} ({len(league_matches)} matches)")
        
        # Calculate League Avgs (Specific to this league)
        league_avgs = stats_service.calculate_league_averages(league_matches)
        
        # Prepare Rolling Stats
        team_stats_cache = {}
        empty_stats = stats_service.create_empty_stats_dict()
        training_tasks = []
        weights = learning_service.get_learning_weights()
        
        for match in league_matches:
            if match.home_goals is None or match.away_goals is None: continue
            
            h_name = match.home_team.name
            a_name = match.away_team.name
            
            # Snapshot state BEFORE match
            raw_home = team_stats_cache.get(h_name, empty_stats).copy()
            raw_away = team_stats_cache.get(a_name, empty_stats).copy()
            
            # Init if new
            if h_name not in team_stats_cache: team_stats_cache[h_name] = raw_home
            if a_name not in team_stats_cache: team_stats_cache[a_name] = raw_away
            
            # Warmup check (> 3 matches)
            if raw_home['matches_played'] >= 3 and raw_away['matches_played'] >= 3:
                training_tasks.append((match, raw_home, raw_away, league_avgs, None, weights))
                
            # Update State
            stats_service.update_team_stats_dict(team_stats_cache[h_name], match, is_home=True)
            stats_service.update_team_stats_dict(team_stats_cache[a_name], match, is_home=False)
            
        # Extract Features Parallel
        if not training_tasks:
            continue
            
        X = []
        y_corners = []
        y_cards = []
        y_outcome = [] # 0=Draw, 1=Home, 2=Away
        
        try:
            results = joblib.Parallel(n_jobs=-1, batch_size=50)(
                joblib.delayed(process_match_task)(task) for task in training_tasks
            )
            
            for feats, targets in results:
                X.append(feats)
                y_corners.append(targets['total_corners'])
                y_cards.append(targets['total_cards'])
                
                outcome = 0 # Draw
                if targets['home_win']: outcome = 1
                elif targets['away_win']: outcome = 2
                y_outcome.append(outcome)
                
        except Exception as e:
            logger.error(f"Feature extraction failed for {league_id}: {e}")
            continue
            
        # --- TRAIN MODELS ---
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        from sklearn.model_selection import TimeSeriesSplit, cross_val_score
        
        # 1. Corners Regressor
        logger.info(f"   📐 Training Corners Regressor ({league_id})...")
        reg_corners = RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_leaf=5, n_jobs=-1, random_state=42)
        
        # Train
        reg_corners.fit(X, y_corners)
        
        # SANITY CHECK: Mode Collapse Detection
        preds = reg_corners.predict(X)
        std_dev = np.std(preds)
        unique, counts = np.unique(np.round(preds), return_counts=True)
        max_dominance = np.max(counts) / len(preds) if len(preds) > 0 else 0
        
        logger.info(f"      - Distribution: StdDev={std_dev:.3f}, MaxDominance={max_dominance:.2%}")
        
        if max_dominance > 0.90:
            logger.error(f"      ❌ MODE COLLAPSE DETECTED in Corners Model for {league_id}! (90% same value). Skipping save.")
        elif std_dev < 0.5:
            logger.warning(f"      ⚠️ Low Variance in Corners Model for {league_id} (StdDev < 0.5). Model might be too conservative.")
            joblib.dump(reg_corners, f"ml_models/{league_id}_corners.joblib")
        else:
            joblib.dump(reg_corners, f"ml_models/{league_id}_corners.joblib")
            
        # 2. Cards Regressor
        logger.info(f"   cards Training Cards Regressor ({league_id})...")
        reg_cards = RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_leaf=5, n_jobs=-1, random_state=42)
        reg_cards.fit(X, y_cards)
        
        # SANITY CHECK (Cards)
        preds_c = reg_cards.predict(X)
        max_dom_c = (np.unique(np.round(preds_c), return_counts=True)[1].max() / len(preds_c)) if len(preds_c) > 0 else 0
        
        if max_dom_c > 0.90:
             logger.error(f"      ❌ MODE COLLAPSE DETECTED in Cards Model for {league_id}! Skipping save.")
        else:
             joblib.dump(reg_cards, f"ml_models/{league_id}_cards.joblib")

        
        # 3. Match Winner Classifier
        logger.info(f"   🏆 Training Outcome Classifier ({league_id})...")
        clf_outcome = RandomForestClassifier(n_estimators=200, max_depth=15, class_weight='balanced', n_jobs=-1, random_state=42)
        scores_acc = cross_val_score(clf_outcome, X, y_outcome, cv=tscv, scoring='accuracy')
        logger.info(f"      - Accuracy: {np.mean(scores_acc):.2%}")
        
        clf_outcome.fit(X, y_outcome)
        joblib.dump(clf_outcome, f"ml_models/{league_id}_winner.joblib")
        
    elapsed = time.time() - start_time
    logger.info(f"🎉 Training Completed in {elapsed:.2f} seconds.")
    
if __name__ == "__main__":
    asyncio.run(main())
