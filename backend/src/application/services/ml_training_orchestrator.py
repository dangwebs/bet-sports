import asyncio
import logging
import os
import warnings
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

# Suppress DeprecationWarnings from utcnow() used in ML libraries
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*utcnow.*")

# ML Imports will be lazy-loaded in the methods that need them
# to prevent memory spikes on startup (Render Free Tier Optimization)
ML_AVAILABLE = True # Assumed true, checked at runtime

from src.domain.services.learning_service import LearningService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.pick_resolution_service import PickResolutionService
from src.application.services.training_data_service import TrainingDataService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.picks_service import PicksService
from src.domain.services.ai_picks_service import AIPicksService
# from src.domain.services.risk_management.risk_manager import RiskManager
from src.domain.entities.entities import Match
from src.infrastructure.cache.cache_service import CacheService
from src.utils.time_utils import get_current_time
from src.core.constants import DEFAULT_LEAGUES
from src.infrastructure.repositories.persistence_repository import PersistenceRepository
from src.application.services.ml_training_orchestrator_helper import _process_single_match_task

logger = logging.getLogger(__name__)

class TrainingResult(BaseModel):
    matches_processed: int
    correct_predictions: int
    accuracy: float
    total_bets: int
    roi: float
    profit_units: float
    market_stats: dict
    match_history: List[Any] = []
    roi_evolution: List[Any] = []
    pick_efficiency: List[Any] = []
    team_stats: dict = {}
    global_averages: dict = {} # Calculated from the entire 10-year dataset

class MLTrainingOrchestrator:
    """
    Application service that orchestrates the entire ML training pipeline.
    Coordinates data fetching, feature extraction, training, and result calculation.
    """

    # Model Path Resolution (Robust against CWD)
    # Saves to backend/ml_picks_classifier.joblib
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from application/services -> src -> backend
    MODEL_FILE_PATH = os.path.join(_current_dir, "..", "..", "..", "ml_picks_classifier.joblib")

    def __init__(
        self,
        training_data_service: TrainingDataService,
        statistics_service: StatisticsService,
        prediction_service: PredictionService,
        learning_service: LearningService,
        resolution_service: PickResolutionService,
        cache_service: CacheService,
        persistence_repository: Optional[PersistenceRepository] = None
    ):
        self.training_data_service = training_data_service
        self.statistics_service = statistics_service
        self.prediction_service = prediction_service
        self.learning_service = learning_service
        self.resolution_service = resolution_service
        self.cache_service = cache_service
        self.persistence_repository = persistence_repository
        self.feature_extractor = MLFeatureExtractor()
        # self.risk_manager = RiskManager()
        
        # Cache Keys
        self.CACHE_KEY_STATUS = "ml_training_status"
        self.CACHE_KEY_MESSAGE = "ml_training_message"
        self.CACHE_KEY_RESULT = "ml_training_result_data"

    async def run_training_pipeline(
        self, 
        league_ids: Optional[List[str]] = None, 
        days_back: int = 550, # Standardized to 550 days (1.5 years)
        start_date: Optional[str] = None,
        force_refresh: bool = False,
        n_jobs: int = -1
    ) -> TrainingResult:
        """
        Executes the full training pipeline and returns a TrainingResult.
        """
        logger.info(f"Starting ML Training Pipeline (leagues={league_ids}, days_back={days_back})")
        
        # Lazy Load ML Libraries
        try:
            from sklearn.ensemble import RandomForestClassifier
            import joblib
        except ImportError:
            RandomForestClassifier = None
            joblib = None
            logger.warning("ML libraries (sklearn, joblib) not found. Training will be skipped.")
            
        try:
            from tqdm import tqdm
        except ImportError:
            tqdm = None
        
        # 0. Set Status to IN_PROGRESS immediately
        # This tells the frontend to hide the Dashboard button but allow navigation
        self.cache_service.set(self.CACHE_KEY_STATUS, "IN_PROGRESS", ttl_seconds=3600)
        self.cache_service.set(self.CACHE_KEY_MESSAGE, "Iniciando orquestación del servidor...", ttl_seconds=3600)
        
        # 1. Initialize logic-dependant services
        # We use Heuristic PicksService for the 2500+ match backtest to save massive overhead
        # The ML model training happens at the end once.
        picks_service_instance = PicksService(learning_weights=self.learning_service.get_learning_weights())
        
        matches_processed = 0
        correct_predictions = 0
        total_bets = 0
        total_staked = 0.0
        total_return = 0.0
        daily_stats = {}
        match_history = []
        
        # ML Training Data accumulation
        ml_features = []
        ml_targets = []
        
        # Team stats cache for rolling historical stats
        team_stats_cache = {}

        try:
            # 2. Fetch & Unify matches (Centralized Orchestration)
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Recuperando datos históricos de múltiples ligas...", ttl_seconds=3600)
            leagues = league_ids if league_ids else DEFAULT_LEAGUES
            all_matches = await self.training_data_service.fetch_comprehensive_training_data(
                leagues=leagues, 
                days_back=days_back, 
                start_date=start_date,
                force_refresh=force_refresh
            )
            
            # Detailed Logging for visibility
            source_stats = {}
            league_stats = {}
            for m in all_matches:
                src = m.id.split('_')[0] if '_' in m.id else "unknown"
                source_stats[src] = source_stats.get(src, 0) + 1
                league_stats[m.league.id] = league_stats.get(m.league.id, 0) + 1
            
            logger.info(f"Fetched {len(all_matches)} total matches. Sources: {source_stats}. Leagues: {league_stats}")
            
        except Exception as e:
            logger.error(f"Failed to fetch training data: {e}")
            self.cache_service.set(self.CACHE_KEY_STATUS, "ERROR", ttl_seconds=3600)
            raise e

        # 3. Pre-calculate REAL league averages
        league_matches_map = {}
        for m in all_matches:
            if m.league.id not in league_matches_map: 
                league_matches_map[m.league.id] = []
            league_matches_map[m.league.id].append(m)
            
        league_averages_map = {
            lid: self.statistics_service.calculate_league_averages(ms) 
            for lid, ms in league_matches_map.items()
        }
        
        # 3b. Calculate GLOBAL averages (Ultimate Fallback)
        global_averages_obj = self.statistics_service.calculate_league_averages(all_matches)
        global_averages = {
            "avg_home_goals": round(global_averages_obj.avg_home_goals, 4),
            "avg_away_goals": round(global_averages_obj.avg_away_goals, 4),
            "avg_total_goals": round(global_averages_obj.avg_total_goals, 4),
            "avg_corners": round(global_averages_obj.avg_corners, 4),
            "avg_cards": round(global_averages_obj.avg_cards, 4)
        }
        self.cache_service.set("global_statistical_averages", global_averages, ttl_seconds=86400 * 7)

        # 4. SORT MATCHES BY DATE (CRITICAL for TimeSeriesSplit)
        # Normalize datetimes to naive for comparison (some sources return aware, others naive)
        def get_sort_key(m):
            dt = m.match_date
            if dt.tzinfo is not None:
                # Convert to naive by removing timezone info (already in local time)
                return dt.replace(tzinfo=None)
            return dt
        
        all_matches.sort(key=get_sort_key)
        
        # --- ROLLING WINDOW BACKTESTING (Day-by-Day Portfolio Simulation) ---
        # We group matches by day to enforce daily risk limits.
        
        from itertools import groupby
        matches_by_day = [list(group) for key, group in groupby(all_matches, key=lambda m: m.match_date.date())]
        
        # CRITICAL Optimization for 512MB RAM: Clear the flat list now that we have it grouped
        del all_matches
        import gc
        gc.collect()
        
        self.cache_service.set(self.CACHE_KEY_MESSAGE, f"Analizando partidos día por día...", ttl_seconds=3600)
        
        # Minimum samples to start using ML model
        MIN_TRAIN_SAMPLES = 50 
        
        try:
            # Console Progress Bar
            iterator = matches_by_day
            if tqdm:
                iterator = tqdm(matches_by_day, desc="Processing Days", unit="day")
                
            for daily_matches in iterator:
            
                # A. Rolling Training DISABLED for performance on 512MB RAM / 0.1 CPU
                # Retraining inside the loop is too heavy. We rely on Heuristics for the backtest,
                # and train the ML model ONLY once at the end.
                # if ML_AVAILABLE and RandomForestClassifier and len(ml_features) >= MIN_TRAIN_SAMPLES:
                #      # Retrain periodically (e.g. every 50 new samples) or every day if fast enough
                #      # For now, let's retrain every ~200 samples to simulate periodic model updates
                #          if len(ml_features) % 200 < len(daily_matches) or len(ml_features) == MIN_TRAIN_SAMPLES:
                #              try:
                #                 # Run CPU-bound training in thread to avoid blocking event loop
                #                 def _train_step(features, targets):
                #                     c = RandomForestClassifier(
                #                         n_estimators=150, 
                #                         max_depth=8, 
                #                         random_state=42, 
                #                         n_jobs=-1,
                #                         class_weight='balanced'
                #                     )
                #                     c.fit(features, targets)
                #                     return c
                #                 
                #                 loop = asyncio.get_running_loop()
                #                 clf = await loop.run_in_executor(None, _train_step, ml_features, ml_targets)
                #                 
                #                 picks_service_instance.ml_model = clf
                #              except Exception as e:
                #                 logger.warning(f"Rolling Window Training Limit: {e}")
    
                # B. Generate Candidates for TODAY (PARALLELIZED)
                daily_candidates = [] # List of {'pick': SuggestedPick, 'match': Match}
                daily_predictions_map = {} # match_id -> Prediction

                # Prepare data for parallel execution to avoid pickling the whole service
                # We explicitly pass only what's needed
                parallel_inputs = []
                for match in daily_matches:
                    if match.home_goals is None or match.away_goals is None: continue
                    
                    # Get stats (fast dict lookup)
                    raw_home = team_stats_cache.get(match.home_team.name, self.statistics_service.create_empty_stats_dict())
                    raw_away = team_stats_cache.get(match.away_team.name, self.statistics_service.create_empty_stats_dict())
                    
                    # Init stats if missing
                    if match.home_team.name not in team_stats_cache: team_stats_cache[match.home_team.name] = raw_home
                    if match.away_team.name not in team_stats_cache: team_stats_cache[match.away_team.name] = raw_away

                    league_averages = league_averages_map.get(match.league.id)
                    
                    parallel_inputs.append((
                        match, 
                        raw_home, 
                        raw_away, 
                        league_averages, 
                        global_averages_obj, 
                        self.prediction_service, 
                        picks_service_instance,
                        self.statistics_service,
                        self.resolution_service,
                        self.feature_extractor,
                        # self.risk_manager
                    ))
                
                # Execute in parallel using all available cores (n_jobs=-1)
                # We use 'loky' backend which is robust for pickling
                if parallel_inputs:
                    from sklearn.utils.parallel import Parallel, delayed
                    
                    # Inner function defined here to be picklable? No, must be top-level or static.
                    # But we can use 'delayed' on a standalone function.
                    # Let's use a helper method defined outside the class or static.
                    # For safety and context, we'll keep it simple:
                    # We can't pickle 'self', so we pass services explicitly.
                    
                    results = Parallel(n_jobs=n_jobs, prefer="threads")(
                        delayed(_process_single_match_task)(*args) for args in parallel_inputs
                    )
                    
                    # Process results
                    for res in results:
                        if not res: continue
                        match_res, pred_res, picks_container_res = res
                        
                        matches_processed += 1
                        daily_predictions_map[match_res.id] = pred_res
                        
                        if picks_container_res and picks_container_res.suggested_picks:
                            for p in picks_container_res.suggested_picks:
                                daily_candidates.append({'pick': p, 'match': match_res, 'prediction': pred_res})
                                
                # C. Apply Portfolio Constraints (Risk Manager)
                # Bypassed: We approve ALL candidates directly
                # approved_items = self.risk_manager.apply_portfolio_constraints(daily_candidates)
                approved_items = daily_candidates
            
            # Mapping for Training (All Candidates) vs Simulation (Approved Only)
            candidate_picks_map = {}
            for item in daily_candidates:
                mid = item['match'].id
                if mid not in candidate_picks_map: candidate_picks_map[mid] = []
                candidate_picks_map[mid].append(item['pick'])

            approved_picks_map = {} 
            for item in approved_items:
                mid = item['match'].id
                if mid not in approved_picks_map: approved_picks_map[mid] = []
                approved_picks_map[mid].append(item['pick'])
    
            # D. Resolve & Record Results
            for match in daily_matches:
                 if match.home_goals is None: continue
                 
                 # PROCESS ALL CANDIDATES for ML Training
                 candidates = candidate_picks_map.get(match.id, [])
                 approved_list = approved_picks_map.get(match.id, [])
                 
                 # Track if *any* pick for this match was approved (for history/display)
                 has_approved_pick = len(approved_list) > 0

                 picks_list = []
                 suggested_pick_label = False
                 pick_was_correct = False
                 max_ev_value = -100.0

                 # We iterate CANDIDATES to ensure comprehensive training data
                 for pick in candidates:
                    result_str, payout = self.resolution_service.resolve_pick(pick, match)
                    is_won = (result_str == "WIN")
                    
                    # Check if this specific pick was approved (for ROI calc)
                    is_approved = any(p == pick for p in approved_list) # Identity check might fail if copies, but usually fine
                    # Better: check pick ID if exists, or just use the approved_list content.
                    # Optimization: Since 'pick' object is likely same instance from memory in 'daily_candidates'
                    is_approved = pick in approved_list

                    p_detail = {
                        "market_type": pick.market_type.value if hasattr(pick.market_type, "value") else str(pick.market_type),
                        "market_label": pick.market_label,
                        "was_correct": is_won,
                        "probability": float(pick.probability),
                        "expected_value": float(pick.expected_value),
                        "confidence": float(pick.priority_score or pick.probability),
                        "reasoning": pick.reasoning,
                        "result": result_str,
                        "suggested_stake": getattr(pick, "suggested_stake", 0.0),
                        "kelly_percentage": getattr(pick, "kelly_percentage", 0.0),
                        "is_ml_confirmed": getattr(pick, "is_ml_confirmed", False),
                        "is_contrarian": float(pick.expected_value) > 0.05
                    }
                    
                    # ALWAYS Extract Features for Training (if pick is valid)
                    # This ensures we train on ALL potential opportunities, not just the ones we took.
                    raw_home_feat = team_stats_cache.get(match.home_team.name, {})
                    raw_away_feat = team_stats_cache.get(match.away_team.name, {})
                    feat_home_stats = self.statistics_service.convert_to_domain_stats(match.home_team.name, raw_home_feat)
                    feat_away_stats = self.statistics_service.convert_to_domain_stats(match.away_team.name, raw_away_feat)
                    
                    ml_features.append(self.feature_extractor.extract_features(pick, match, feat_home_stats, feat_away_stats))
                    ml_targets.append(1 if is_won else 0)
                    
                    # ONLY Track ROI if Approved
                    if is_approved:
                        if p_detail["market_type"] in ["winner", "draw", "result_1x2"]:
                             total_bets += 1
                             total_staked += p_detail["suggested_stake"] 
                             total_return += (p_detail["suggested_stake"] * payout) if payout > 0 else 0
                             if float(pick.expected_value) > max_ev_value:
                                  suggested_pick_label = pick.market_label
                                  pick_was_correct = is_won
                                  max_ev_value = float(pick.expected_value)

                        # Daily stats update (ROI)
                        date_key = match.match_date.strftime("%Y-%m-%d")
                        if date_key not in daily_stats: 
                            daily_stats[date_key] = {'staked': 0.0, 'return': 0.0, 'count': 0}
                        daily_stats[date_key]['staked'] += p_detail["suggested_stake"]
                        daily_stats[date_key]['return'] += (p_detail["suggested_stake"] * payout) if payout > 0 else 0
                        daily_stats[date_key]['count'] += 1
                        
                        # Add to display list
                        picks_list.append(p_detail)

                    # CLV Tracking (Keep for all or just approved? Let's keep for approved logic below)
                    # Actually, p_detail is only used for display list if approved.
                    
                 # History Logging (Only if we had approved bets OR significant candidates?)
                 # To limit noise, let's only log matches where we had ACTION.
                 if has_approved_pick:
                     pred_obj = daily_predictions_map.get(match.id)
                     if pred_obj:
                         if len(match_history) > 500: match_history.pop(0)
                         match_history.append({
                             "match_id": match.id,
                             "home_team": match.home_team.name,
                             "away_team": match.away_team.name,
                             "match_date": match.match_date.isoformat(),
                             "predicted_winner": self._get_predicted_winner(pred_obj),
                             "actual_winner": self._get_actual_winner(match),
                             "predicted_home_goals": round(pred_obj.predicted_home_goals, 2),
                             "predicted_away_goals": round(pred_obj.predicted_away_goals, 2),
                             "actual_home_goals": match.home_goals,
                             "actual_away_goals": match.away_goals,
                             "was_correct": self._get_predicted_winner(pred_obj) == self._get_actual_winner(match),
                             "confidence": round(pred_obj.confidence, 3),
                             "picks": picks_list, # Only approved picks
                             "suggested_pick": suggested_pick_label,
                             "pick_was_correct": pick_was_correct,
                             "expected_value": max_ev_value
                         })

            # E. Update Stats (After Day is Done) - The "Nightly Update"
            # Crucial: We update stats using ALL matches of the day, even those we didn't bet on.
            # E. Update Stats (After Day is Done) - The "Nightly Update"
            # Crucial: We update stats using ALL matches of the day, even those we didn't bet on.
            for match in daily_matches:
                if match.home_team.name in team_stats_cache:
                    self.statistics_service.update_team_stats_dict(team_stats_cache[match.home_team.name], match, is_home=True)
                if match.away_team.name in team_stats_cache:
                    self.statistics_service.update_team_stats_dict(team_stats_cache[match.away_team.name], match, is_home=False)
            
            # Yield control to event loop to allow other requests (health checks, polling) to be processed
            await asyncio.sleep(0)
        
            # --- TRAIN ML MODEL ---
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Entrenando modelo de Machine Learning (Random Forest)...", ttl_seconds=3600)
            
            # CRITICAL: Force Garbage Collection before training to free up RAM
            import gc
            gc.collect()

            logger.info(f"ML Debug: ML_AVAILABLE={ML_AVAILABLE}, Features={len(ml_features)}")

            if ML_AVAILABLE and RandomForestClassifier and len(ml_features) > 100:
                try:
                    logger.info(f"Training ML Model on {len(ml_features)} samples...")
                    
                    # Offload CPU-bound training to a thread
                    # Offload CPU-bound training to a thread
                    def _train_and_save():
                        # Optimized for LOW MEMORY (Render Free Tier - 512MB RAM):
                        # - n_estimators=100 (reduced from 200)
                        # - max_depth=10 (reduced from 12) to prevent potential overfitting and save memory
                        # - n_jobs=1 (CRITICAL: Avoid multiprocessing overhead in container)
                        clf = RandomForestClassifier(
                            n_estimators=1000,
                            max_depth=25,
                            min_samples_split=5,
                            min_samples_leaf=2,
                            random_state=42,
                            n_jobs=-1,  # Use all available cores
                            class_weight="balanced_subsample"
                        )
                        clf.fit(ml_features, ml_targets)
                        
                        # Save to absolute path
                        joblib.dump(clf, self.MODEL_FILE_PATH)
                        return clf
    
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, _train_and_save)
                    
                    logger.info("ML Model trained and saved.")
                except Exception as e:
                    logger.error(f"Failed to train ML model: {e}")
            
            else:
                logger.error(f"Skipping ML Training. Data insufficient or libraries missing. Features: {len(ml_features)}")
                if len(ml_features) <= 100:
                    raise Exception(f"Insufficient training data: {len(ml_features)} samples (min 100)")
            
            # --- PREPARE RESULTS ---
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Consolidando métricas y evolución de ROI...", ttl_seconds=3600)
            accuracy = self._calculate_accuracy(match_history)
            profit = total_return - total_staked
            roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
            
            final_result = TrainingResult(
                matches_processed=matches_processed,
                correct_predictions=self._get_correct_count(match_history),
                accuracy=round(accuracy, 4),
                total_bets=total_bets,
                roi=round(roi, 2),
                profit_units=round(profit, 2),
                market_stats=self.learning_service.get_all_stats(),
                match_history=match_history,
                roi_evolution=self._calculate_roi_evolution(daily_stats),
                pick_efficiency=self._calculate_pick_efficiency(match_history),
                team_stats=team_stats_cache,
                global_averages=global_averages
            )
            
            # Optimization: Clear match_history from memory-intensive objects
            del match_history
            del team_stats_cache
            gc.collect()
            
            # Save result to cache and update status
            # This enables the "Bot Dashboard" button on the frontend
            # Save result to cache and update status
            # This enables the "Bot Dashboard" button on the frontend
            # Use simple dict conversion that handles nested models if possible, else rely on Pydantic's dict()
            # Note: TrainingResult is a Pydantic model, so .dict() or .model_dump() works
            result_data = final_result.model_dump() if hasattr(final_result, 'model_dump') else final_result.dict()
            
            self.cache_service.set(self.CACHE_KEY_RESULT, result_data, ttl_seconds=self.cache_service.TTL_TRAINING)
            self.cache_service.set(self.CACHE_KEY_STATUS, "COMPLETED", ttl_seconds=self.cache_service.TTL_TRAINING)
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Entrenamiento completado exitosamente", ttl_seconds=self.cache_service.TTL_TRAINING)
            
            # Persistent DB storage (Fallback for ephemeral local storage like Render)
            if self.persistence_repository:
                logger.info("Persisting training result to PostgreSQL...")
                self.persistence_repository.save_training_result("latest_daily", result_data)

            # 6. MASSIVE INFERENCE: SKIPPED
            # Predictions are already saved to PostgreSQL in the run_predictions.py worker (Step 2).
            # Calling GetPredictionsUseCase.execute() again would make redundant API calls.
            # If cache warming is needed, it should be done without external API calls.
            logger.info("Skipping massive inference step (predictions already saved in worker Step 2)")
                
            return final_result

        except asyncio.CancelledError:
            logger.warning("ML Training Pipeline was cancelled. Cleaning up...")
            self.cache_service.set(self.CACHE_KEY_STATUS, "CANCELLED", ttl_seconds=3600)
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Entrenamiento cancelado.", ttl_seconds=3600)
            raise 
        except Exception as e:
            logger.error(f"Critical error in training pipeline: {e}")
            self.cache_service.set(self.CACHE_KEY_STATUS, "ERROR", ttl_seconds=3600)
            self.cache_service.set(self.CACHE_KEY_MESSAGE, f"Error crítico: {str(e)}", ttl_seconds=3600)
            raise e

    def _get_predicted_winner(self, prediction) -> str:
        if prediction.home_win_probability > prediction.away_win_probability and prediction.home_win_probability > prediction.draw_probability:
            return "home"
        elif prediction.away_win_probability > prediction.home_win_probability and prediction.away_win_probability > prediction.draw_probability:
            return "away"
        return "draw"

    def _get_actual_winner(self, match) -> str:
        if match.home_goals > match.away_goals: return "home"
        elif match.away_goals > match.home_goals: return "away"
        return "draw"

    def _get_correct_count(self, history: List[dict]) -> int:
        return sum(1 for m in history if m["was_correct"])

    def _calculate_accuracy(self, history: List[dict]) -> float:
        if not history: return 0.0
        return self._get_correct_count(history) / len(history)

    def _calculate_roi_evolution(self, daily_stats: dict) -> List[dict]:
        roi_evolution = []
        cum_staked = 0.0
        cum_return = 0.0
        for date_str in sorted(daily_stats.keys()):
            stats = daily_stats[date_str]
            cum_staked += stats['staked']
            cum_return += stats['return']
            profit = cum_return - cum_staked
            roi = (profit / cum_staked * 100) if cum_staked > 0 else 0.0
            roi_evolution.append({"date": date_str, "roi": round(roi, 2), "profit": round(profit, 2)})
        return roi_evolution

    def _calculate_pick_efficiency(self, history: List[dict]) -> List[dict]:
        pick_type_stats = {}
        for match in history:
            for pick in match["picks"]:
                ptype = pick["market_type"]
                if ptype not in pick_type_stats:
                    pick_type_stats[ptype] = {"won": 0, "lost": 0, "void": 0, "total": 0}
                pick_type_stats[ptype]["total"] += 1
                if pick["was_correct"]: pick_type_stats[ptype]["won"] += 1
                else: pick_type_stats[ptype]["lost"] += 1
        
        results = []
        for ptype, data in pick_type_stats.items():
            efficiency = (data["won"] / data["total"] * 100) if data["total"] > 0 else 0.0
            results.append({
                "pick_type": ptype, "won": data["won"], "lost": data["lost"],
                "void": data["void"], "total": data["total"], "efficiency": round(efficiency, 2)
            })
        results.sort(key=lambda x: x["efficiency"], reverse=True)
        return results

    async def execute_massive_inference_step(self, leagues: List[str]):
        """
        Pre-calculates all match predictions and suggested picks for all leagues.
        This data is persisted in PostgreSQL to ensure instant access for users.
        """
        logger.info(f"Starting MASSIVE INFERENCE for {len(leagues)} leagues...")
        self.cache_service.set(self.CACHE_KEY_MESSAGE, f"Pre-calculando pronósticos para {len(leagues)} ligas...", ttl_seconds=3600)
        
        from src.application.use_cases.use_cases import GetPredictionsUseCase, DataSources
        
        # We re-use orchestrator's knowledge to build the Use Case
        # This keeps logic in sync between the API and the Training Cycle
        use_case = GetPredictionsUseCase(
            data_sources=DataSources(
                football_data_uk=self.training_data_service.data_sources.football_data_uk,
                football_data_org=self.training_data_service.data_sources.football_data_org,
                openfootball=self.training_data_service.data_sources.openfootball,
                thesportsdb=self.training_data_service.data_sources.thesportsdb,
                fotmob=self.training_data_service.data_sources.fotmob
            ),
            prediction_service=self.prediction_service,
            statistics_service=self.statistics_service,
            persistence_repository=self.persistence_repository
        )

        for league_id in leagues:
            try:
                # Execute generating and persisting the forecast
                logger.info(f"Inference: Processing {league_id}...")
                await use_case.execute(league_id)
            except Exception as e:
                logger.error(f"Inference failed for league {league_id}: {e}")
                continue
        
        logger.info("MASSIVE INFERENCE step completed.")
