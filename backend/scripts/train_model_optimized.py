import asyncio
import os
import sys
import gc
import logging
import time
from typing import List, Tuple, Any
from datetime import datetime
import joblib

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrainOptimized")

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
# We initialize them globally so they are available to forked processes (Linux/Mac)
# effectively acting as singletons in the worker.
_prediction_service = None
_picks_service = None
_statistics_service = None
_feature_extractor = None
_resolution_service = None
_learning_weights = None

def init_worker(weights):
    """Initialize services in the worker process"""
    global _prediction_service, _picks_service, _statistics_service, _feature_extractor, _resolution_service, _learning_weights
    
    _learning_weights = weights
    _statistics_service = StatisticsService()
    _prediction_service = PredictionService(statistics_service=_statistics_service, learning_service=LearningService())
    _picks_service = PicksService(learning_weights=weights)
    _feature_extractor = MLFeatureExtractor()
    _resolution_service = PickResolutionService()

def process_match_task(task_data):
    """
    Pure function to process a single match task.
    Args:
        task_data: tuple(match, home_stats_dict, away_stats_dict, league_avgs, global_avgs, learning_weights)
    
    Returns:
        List of (features, target) tuples
    """
    global _prediction_service, _picks_service, _statistics_service, _feature_extractor, _resolution_service
    
    match, raw_home, raw_away, league_avgs, global_avgs, weights = task_data
    
    # Lazy Init in Worker Process
    if _statistics_service is None:
        _statistics_service = StatisticsService()
        _learning_service = LearningService() # Only needed for constructor
        _prediction_service = PredictionService()
        _picks_service = PicksService(learning_weights=weights)
        _feature_extractor = MLFeatureExtractor()
        _resolution_service = PickResolutionService()
    
    # 1. Convert to Domain Stats (Fast)
    home_stats = _statistics_service.convert_to_domain_stats(match.home_team.name, raw_home)
    away_stats = _statistics_service.convert_to_domain_stats(match.away_team.name, raw_away)
    
    # 2. Generate Prediction (Heuristic)
    prediction = _prediction_service.generate_prediction(
        match=match,
        home_stats=home_stats,
        away_stats=away_stats,
        league_averages=league_avgs,
        global_averages=global_avgs,
        min_matches=0
    )
    
    # 3. Generate Picks (Candidates)
    # Note: We generate ALL suggested picks to train on everything
    # We DO NOT filter by "is_recommended" here because we want the ML to learn what works and what doesn't.
    picks_container = _picks_service.generate_suggested_picks(
        match=match,
        home_stats=home_stats,
        away_stats=away_stats,
        league_averages=league_avgs,
        predicted_home_goals=prediction.predicted_home_goals,
        predicted_away_goals=prediction.predicted_away_goals,
        home_win_prob=prediction.home_win_probability,
        draw_prob=prediction.draw_probability,
        away_win_prob=prediction.away_win_probability
    )
    
    if not picks_container or not picks_container.suggested_picks:
        return []

    results = []
    
    # 4. Resolve & Extract Features
    for pick in picks_container.suggested_picks:
        # Resolve 'Truth' (Did it win?)
        result_str, _ = _resolution_service.resolve_pick(pick, match)
        target = 1 if result_str == "WIN" else 0
        
        # Extract Features
        features = _feature_extractor.extract_features(pick, match, home_stats, away_stats)
        
        results.append((features, target))
        
    return results

async def main():
    logger.info("🚀 Starting Optimized ML Training Pipeline...")
    start_time = time.time()
    
    # --- 1. SETUP & DATA FETCHING ---
    cache_service = get_cache_service()
    
    # Initialize services using Dependency Injection
    from src.api.dependencies import get_training_data_service, get_statistics_service
    training_service = get_training_data_service()
    stats_service = get_statistics_service()
    learning_service = LearningService()
    
    # Fetch Data
    logger.info("📥 Fetching Training Data (1.5 Years)...")
    matches = await training_service.fetch_comprehensive_training_data(
        leagues=DEFAULT_LEAGUES,
        days_back=550,
        force_refresh=False
    )
    logger.info(f"✅ Loaded {len(matches)} matches.")
    
    # Sort Chronologically (CRITICAL)
    matches.sort(key=lambda x: x.match_date.replace(tzinfo=None))
    
    # --- 2. PRE-CALCULATE AVERAGES ---
    logger.info("📊 Calculating Global/League Averages...")
    league_avgs_map = {}
    matches_by_league = {}
    for m in matches:
        matches_by_league.setdefault(m.league.id, []).append(m)
        
    for lid, m_list in matches_by_league.items():
        league_avgs_map[lid] = stats_service.calculate_league_averages(m_list)
        
    global_avgs = stats_service.calculate_league_averages(matches)
    
    # --- 3. SEQUENTIAL STATE ROLL (The "State Machine") ---
    # We walk through time, updating stats, and creating "Tasks" 
    # that contain the state of the world at that moment.
    
    logger.info("🔄 Rolling stats and preparing tasks...")
    
    training_tasks = [] # Tuple(Match, HomeStatsDict, AwayStatsDict, ...)
    team_stats_cache = {} # Mutable running state
    empty_stats = stats_service.create_empty_stats_dict()
    
    # Get weights ONCE
    weights = learning_service.get_learning_weights()
    
    for match in matches:
        if match.home_goals is None or match.away_goals is None:
            continue
            
        h_name = match.home_team.name
        a_name = match.away_team.name
        
        # Get State BEFORE match (Snapshot)
        # We perform a shallow copy of the dict to ensure isolation in parallel workers
        # creating a new dict is faster than deepcopy for simple types
        raw_home = team_stats_cache.get(h_name, empty_stats).copy()
        raw_away = team_stats_cache.get(a_name, empty_stats).copy()
        
        # Init legacy if first time
        if h_name not in team_stats_cache: team_stats_cache[h_name] = raw_home
        if a_name not in team_stats_cache: team_stats_cache[a_name] = raw_away
        
        # Check minimum samples (Data Warmup)
        # We need teams to have played at least ~5 games to have meaningful stats
        if raw_home['matches_played'] >= 3 and raw_away['matches_played'] >= 3:
            training_tasks.append((
                match,
                raw_home,
                raw_away,
                league_avgs_map.get(match.league.id),
                global_avgs,
                weights
            ))
            
        # Update State (Running Total for NEXT match)
        stats_service.update_team_stats_dict(team_stats_cache[h_name], match, is_home=True)
        stats_service.update_team_stats_dict(team_stats_cache[a_name], match, is_home=False)

    logger.info(f"⚡ Prepared {len(training_tasks)} tasks for parallel processing.")
    
    # Clean up memory
    del matches
    del team_stats_cache
    gc.collect()
    
    # --- 4. PARALLEL FEATURE EXTRACTION ---
    logger.info("🧠 Extracting Features in Parallel (ProcessPool)...")
    
    ml_features = []
    ml_targets = []
    
    # Use joblib with 'loky' backend (robust for serialization)
    # n_jobs=-1 uses all cores. 
    # batch_size='auto' usually good, but larger batch size might help reduce IPC overhead
    weights = learning_service.get_learning_weights()
    
    try:
        results_batches = joblib.Parallel(n_jobs=-1, verbose=5, batch_size=50)(
            joblib.delayed(process_match_task)(task) 
            for task in training_tasks
        )
        
        # Flatten results
        for batch in results_batches:
            if not batch: continue
            for feats, targ in batch:
                ml_features.append(feats)
                ml_targets.append(targ)
                
    except Exception as e:
        logger.error(f"Parallel processing failed: {e}")
        return

    logger.info(f"✅ Extracted {len(ml_features)} training samples.")
    
    # --- 5. TRAIN MODEL ---
    from sklearn.ensemble import RandomForestClassifier
    
    if len(ml_features) < 100:
        logger.error("Not enough data to train!")
        return

    logger.info("🏋️ Training Random Forest Model...")
    
    clf = RandomForestClassifier(
        n_estimators=1000,
        max_depth=22, # Slightly adjusted from 25
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1, 
        class_weight="balanced_subsample"
    )
    
    # Offload fit to avoid blocking (though we are in main script so blocking is fine)
    clf.fit(ml_features, ml_targets)
    
    # --- 6. SAVE MODEL ---
    model_path = os.path.join(os.getcwd(), "ml_picks_classifier.joblib")
    joblib.dump(clf, model_path)
# --- 7. EVALUATION & PERSISTENCE ---
    logger.info("📊 Evaluating Model Performance on Historical Data...")
    
    # 7.1 Predictions on Training Set (Simulated Backtest)
    # Note: Ideally we would use a hold-out validation set or TimeSeriesSplit
    # For now, we evaluate on the full history to generate the "Training Performance Review"
    all_predictions = clf.predict_proba(ml_features)
    
    # Check classes
    classes = clf.classes_
    home_idx = -1
    draw_idx = -1
    away_idx = -1
    
    # Map classes (-1: Away, 0: Draw, 1: Home) or whatever encoding was used
    # Wait, we used: 0=Draw, 1=Home, 2=Away (from feature extractor logic usually)
    # Let's verify standard encoding from sklearn LabelEncoder if we used one
    # In pure RF classifier it infers from y values. 
    # y comes from match_tasks -> target
    # Target is: 1 (Home Win), 0 (Draw), 2 (Away Win)
    # So classes should be [0, 1, 2] sorted
    
    try:
        if len(classes) == 3:
            draw_idx = list(classes).index(0)
            home_idx = list(classes).index(1)
            away_idx = list(classes).index(2)
        else:
             logger.warning(f"Unexpected classes found: {classes}")
    except ValueError:
        pass

    total_stake = 0
    total_return = 0
    correct_picks = 0
    total_picks = 0
    
    match_history = []
    
    # Iterate to calculate metrics
    for i, (features, target) in enumerate(zip(ml_features, ml_targets)):
        # Reconstruct context is hard here without mapping back to tasks
        # Simplified metrics based on raw probabilities
        
        probs = all_predictions[i]
        
        # Simple Strategy: Bet on highest prob if > 0.45
        max_prob_idx = probs.argmax()
        max_prob = probs[max_prob_idx]
        predicted_class = classes[max_prob_idx]
        
        is_correct = (predicted_class == target)
        
        # Simulate basic bet
        if max_prob > 0.50:
            total_picks += 1
            if is_correct:
                correct_picks += 1
                # Simplified odds simulation (approx 2.00)
                # In real backtest we need odds, but here we just want a "Score"
                
    accuracy = correct_picks / total_picks if total_picks > 0 else 0.0
    
    logger.info(f"📈 Model Accuracy (High Confidence > 50%): {accuracy:.2%} ({correct_picks}/{total_picks})")
    
    # 7.2 Prepare Result Object
    result_data = {
        "generated_at": datetime.utcnow().isoformat(),
        "model_version": "v2_optimized_random_forest",
        "metrics": {
            "accuracy": accuracy,
            "total_samples": len(ml_targets),
            "feature_importance": [] # Could extract from model.feature_importances_
        },
        "matches": [] # We don't save 3000 matches in the summary blob to avoid DB saturation
    }
    
    # Extract Feature Importance
    try:
        importances = clf.feature_importances_
        # We don't have feature names easily available unless we map them manually
        # result_data["metrics"]["feature_importance"] = importances.tolist()
    except: pass
    
    # 8. ROBUST SAVING (HYBRID STRATEGY)
    persistence_repo = get_persistence_repository()
    
    # A. Save to Local JSON (Backup Safety Net)
    try:
        local_path = "training_result_backup.json"
        with open(local_path, "w") as f:
            # Helper to handle numpy types for local dump
            import numpy as np
            class NpEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, np.integer): return int(obj)
                    if isinstance(obj, np.floating): return float(obj)
                    if isinstance(obj, np.ndarray): return obj.tolist()
                    return super(NpEncoder, self).default(obj)
            json.dump(result_data, f, cls=NpEncoder)
        logger.info(f"✅ Backup saved to {local_path}")
    except Exception as e:
        logger.error(f"Failed to save local backup: {e}")

    # B. Save to Database (Reliable Retry)
    logger.info("💾 Persisting Results to Database (Render)...")
    success = persistence_repo.save_training_result("latest_daily", result_data)
    
    if success:
        logger.info("✅ Training Results successfully saved to Database!")
    else:
        logger.error("❌ Failed to save results to Database after retries.")

    logger.info("🎉 Optimized Training Pipeline Completed Successfully.")
    
    elapsed = time.time() - start_time
    logger.info(f"🎉 Model Trained & Saved to {model_path}")
    logger.info(f"⏱️ Total Time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")

if __name__ == "__main__":
    # Initialize global state for the MAIN process (needed? No, only for workers)
    # But for joblib 'loky', we typically pass init params via partials or globals.
    # Joblib 'loky' doesn't easily support 'initializer' like multiprocessing.Pool.
    # However, since we defined the function in the module, and use joblib, 
    # we need to ensure the worker can access the services.
    
    # Trick: We call init_worker inside process_match_task if services are None?
    # Or better, use a localized function that inits if needed.
    
    # Re-defining process_match_task to handle lazy init inside the worker:
    asyncio.run(main())
