"""
Application Use Cases Module

Use cases represent application-specific business rules and orchestrate
the flow of data between the domain layer and the infrastructure layer.
"""

from datetime import datetime
from typing import Optional, List, Any
from dataclasses import dataclass
from pytz import timezone
import logging
from src.infrastructure.services.background_processor import BackgroundProcessor

from src.domain.entities.entities import Match, League, Prediction, TeamStatistics
# from src.domain.services.risk_management.risk_manager import RiskManager
from src.domain.services.prediction_service import PredictionService
from src.domain.services.picks_service import PicksService
from src.domain.services.ai_picks_service import AIPicksService
from src.domain.services.match_aggregator_service import MatchAggregatorService
from src.infrastructure.repositories.mongo_repository import MongoRepository
from src.domain.value_objects.value_objects import LeagueAverages
from src.domain.exceptions import InsufficientDataException
from src.infrastructure.data_sources.football_data_uk import (
    FootballDataUKSource,
    LEAGUES_METADATA,
)
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
import asyncio

from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
from src.infrastructure.data_sources.espn import ESPNSource
from src.infrastructure.data_sources.club_elo import ClubEloSource
from src.application.dtos.dtos import (
    TeamDTO,
    LeagueDTO,
    MatchDTO,
    PredictionDTO,
    MatchPredictionDTO,
    CountryDTO,
    LeaguesResponseDTO,
    PredictionsResponseDTO,
)
from src.application.use_cases.suggested_picks_use_case import (
    GetSuggestedPicksUseCase,
    RegisterFeedbackUseCase,
    GetLearningStatsUseCase,
    GetTopMLPicksUseCase
)
import joblib
import os
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.entities.suggested_pick import SuggestedPick, MarketType, ConfidenceLevel


logger = logging.getLogger(__name__)


@dataclass
class DataSources:
    """Container for all data sources."""
    football_data_uk: FootballDataUKSource
    football_data_org: FootballDataOrgSource
    openfootball: OpenFootballSource
    thesportsdb: TheSportsDBClient
    espn: Optional[ESPNSource] = None
    club_elo: Optional[ClubEloSource] = None


class GetLeaguesUseCase:
    """Use case for getting available leagues."""
    
    def __init__(self, data_sources: DataSources):
        self.data_sources = data_sources
    
    async def execute(self) -> LeaguesResponseDTO:
        """Get all available leagues grouped by country."""
        from src.core.constants import DEFAULT_LEAGUES
        
        # Get all default leagues using metadata
        leagues = []
        for lid in DEFAULT_LEAGUES:
            if lid in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[lid]
                leagues.append(League(
                    id=lid,
                    name=meta["name"],
                    country=meta["country"],
                ))
        
        # Group by country
        countries_dict: dict[str, list[League]] = {}
        for league in leagues:
            if league.country not in countries_dict:
                countries_dict[league.country] = []
            countries_dict[league.country].append(league)
        
        # Build response
        countries = []
        for country_name, country_leagues in sorted(countries_dict.items()):
            league_dtos = [
                LeagueDTO(
                    id=league.id,
                    name=league.name,
                    country=league.country,
                    season=league.season,
                )
                for league in country_leagues
            ]
            countries.append(CountryDTO(
                name=country_name,
                code=country_name[:3].upper(),
                leagues=league_dtos,
            ))
        
        return LeaguesResponseDTO(
            countries=countries,
            total_leagues=len(leagues),
        )


from src.domain.services.statistics_service import StatisticsService

class GetPredictionsUseCase:
    """Use case for getting match predictions."""
    
    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        match_aggregator: MatchAggregatorService,
        # risk_manager: RiskManager,
        persistence_repository: Optional["MongoRepository"] = None,
        background_processor: Optional[BackgroundProcessor] = None,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.match_aggregator = match_aggregator
        # self.risk_manager = risk_manager
        self.persistence_repository = persistence_repository
        from src.domain.services.learning_service import LearningService
        self.picks_service = AIPicksService(learning_weights=get_learning_service().get_learning_weights() if 'get_learning_service' in globals() else {})

        self.background_processor = background_processor
        
        # Load ML Model for Rigorous Probability Calculation
        self.ml_model = None
        try:
            # Path relative to backend/src/application/use_cases/ -> backend/ml_picks_classifier.joblib
            # Based on orchestrator path: backend/src/application/services/../../../ml_picks_classifier.joblib
            model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../backend/ml_picks_classifier.joblib'))
            # Fallback check
            if not os.path.exists(model_path):
                 model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../ml_picks_classifier.joblib'))
            
            if os.path.exists(model_path):
                self.ml_model = joblib.load(model_path)
                logger.info(f"✅ Loaded ML Model for rigorous probabilities from {model_path}")
            else:
                logger.warning(f"⚠️ ML Model not found at {model_path}. Using heuristic probabilities.")
        except Exception as e:
            logger.error(f"❌ Failed to load ML model: {e}")
    
    async def execute(self, league_id: str, limit: int = 20, force_refresh: bool = False) -> PredictionsResponseDTO:
        """
        Get predictions for upcoming matches in a league.
        
        Args:
            league_id: League identifier
            limit: Maximum matches to return
            
        Returns:
            Predictions response with match predictions
        """
        # Get league metadata
        if league_id not in LEAGUES_METADATA:
            raise ValueError(f"Unknown league: {league_id}")
            
        # 0. Check Cache (Ephemeral & Persistent)
        from src.infrastructure.cache.cache_service import get_cache_service
        cache_service = get_cache_service()
        
        # Unified Cache Key for League Forecasts
        cache_key = f"forecasts:league_{league_id}"
        
        if force_refresh:
            logger.info(f"🔄 Force Refresh requested for {league_id}. Skipping cache lookup.")
        else:
            # 0.1 Check for new data in DB first (Versioning/Sync)
            db_data, db_last_updated = (None, None)
            if self.persistence_repository:
                db_data, db_last_updated = self.persistence_repository.get_training_result_with_timestamp(cache_key)
            
            # 0.2 Try Ephemeral Cache (Memory/Disk)
            cached_response = cache_service.get(cache_key)
            
            # SYNC LOGIC: If we have cached response, check if it's stale compared to DB
            is_stale = False
            if cached_response and db_last_updated:
                try:
                    # Use 'generated_at' from cache or a specific 'cached_db_timestamp'
                    # PredictionsResponseDTO.generated_at is ISO string if cached as dict
                    from src.utils.time_utils import to_colombia_time
                    if cached_response.get('generated_at'):
                        from datetime import timedelta
                        from datetime import timezone as dt_timezone
                        
                        from datetime import datetime as dt
                        gen_at_val = cached_response['generated_at']
                        
                        if isinstance(gen_at_val, dt):
                            gen_at = gen_at_val
                        else:
                            # Handle Z suffix for older python versions compat
                            if gen_at_val.endswith('Z'):
                                gen_at_val = gen_at_val[:-1] + '+00:00'
                            gen_at = dt.fromisoformat(gen_at_val)
                        
                        if gen_at.tzinfo is None:
                                gen_at = gen_at.replace(tzinfo=dt_timezone.utc)
                        else:
                                gen_at = gen_at.astimezone(dt_timezone.utc)
                                
                        # DB Timestamp is typically naive UTC in SQLAlchemy
                        if db_last_updated.tzinfo is None:
                            db_last_updated = db_last_updated.replace(tzinfo=dt_timezone.utc)
                        else:
                            db_last_updated = db_last_updated.astimezone(dt_timezone.utc)
                        
                        # Add a small buffer (e.g. 10 seconds) to avoid race conditions
                        if db_last_updated > (gen_at + timedelta(seconds=10)):
                            logger.info(f"🔄 Cache stale for {league_id} (DB: {db_last_updated} > Cache: {gen_at}). Refreshing...")
                            is_stale = True
                        else:
                                logger.info(f"✓ Cache valid for {league_id}. DB: {db_last_updated} <= Cache: {gen_at}")
                except Exception as e:
                    logger.warning(f"Error comparing cache vs db timestamp: {e}")
                    # If error in comparison, err on side of caution if DB data exists
                    if db_data:
                        is_stale = True

            if cached_response and not is_stale:
                logger.info(f"Serving cached (ephemeral) predictions for {league_id}")
                response = PredictionsResponseDTO(**cached_response)
                
                # STRICT DATE FILTERING (even for cache)
                filtered = self._filter_future_matches(response.predictions)
                if len(filtered) != len(response.predictions):
                    logger.info(f"Filtered {len(response.predictions) - len(filtered)} past matches from cached {league_id}")
                    response.predictions = filtered
                
                return response
                
            # 0.3 Try Persistent DB (PostgreSQL fallback)
            if db_data:
                logger.info(f"Serving persistent (PostgreSQL) predictions for {league_id}")
                # Warm up ephemeral cache for next time
                cache_service.set(cache_key, db_data, ttl_seconds=86400)
                response = PredictionsResponseDTO(**db_data)
                
                # STRICT DATE FILTERING
                filtered = self._filter_future_matches(response.predictions)
                if len(filtered) != len(response.predictions):
                    logger.info(f"Filtered {len(response.predictions) - len(filtered)} past matches from DB {league_id}")
                    response.predictions = filtered
                
                return response
        
        # 0.3 Check if running in API-only mode
        import os
        api_only_mode = os.getenv("API_ONLY_MODE", "false").lower() == "true"
        
        if api_only_mode:
            # In API-only mode, we don't compute predictions - only serve from cache/DB
            logger.warning(f"API-ONLY MODE: No cached predictions found for {league_id}")
            logger.info("💡 Predictions will be available after GitHub Actions worker runs")
            
            # Return empty response instead of error to avoid breaking frontend
            meta = LEAGUES_METADATA[league_id]
            return PredictionsResponseDTO(
                league=LeagueDTO(
                    id=league_id,
                    name=meta["name"],
                    country=meta["country"],
                ),
                predictions=[],
                generated_at=datetime.now(timezone('America/Bogota'))
            )
        
        # If not in API-only mode, proceed with real-time computation
        logger.info(f"Cache miss for {league_id}. Computing predictions in real-time...")
        
        meta = LEAGUES_METADATA[league_id]
        league = League(
            id=league_id,
            name=meta["name"],
            country=meta["country"],
        )
        
        # Get historical data
        # 1. Dynamic Season Calculation
        # Instead of hardcoding "2425", we calculate based on current date
        now = datetime.now(timezone('America/Bogota'))
        current_year = now.year
        
        # Football seasons usually run from July to June
        if now.month < 7:
            # We are in the second half of a season (e.g. Feb 2025 -> 24/25)
            s1_start = current_year - 1
            s1_end = current_year
            s2_start = current_year - 2
            s2_end = current_year - 1
        else:
            # We are in the first half of a season (e.g. Sep 2025 -> 25/26)
            s1_start = current_year
            s1_end = current_year + 1
            s2_start = current_year - 1
            s2_end = current_year
            
        current_season = f"{str(s1_start)[-2:]}{str(s1_end)[-2:]}"
        prev_season = f"{str(s2_start)[-2:]}{str(s2_end)[-2:]}"
        seasons = [current_season, prev_season]
        
        
        logger.info(f"Fetching data for {league_id} via Aggregator Service...")
        
        # 1. Fetch History Aggregated
        historical_matches = await self.match_aggregator.get_aggregated_history(
            league_id,
            seasons=seasons
        )

        # 2. Fetch Upcoming Aggregated
        upcoming_matches = await self.match_aggregator.get_upcoming_matches(
            league_id,
            limit=1000 # Fetch plenty, filter later
        )
        
        # Calculate league averages from historical data using the service
        league_averages = self.statistics_service.calculate_league_averages(historical_matches)
        
        # Strict Date Filter: Only show matches in the future
        # Ensure 'now' and 'match.match_date' are comparable (timezone-aware)
        from src.utils.time_utils import get_current_time
        now = get_current_time() # Returns Bogota time
        
        filtered_upcoming = []
        for m in upcoming_matches:
            # Ensure match date is timezone aware (convert to Bogota if needed)
            m_date = m.match_date
            if m_date.tzinfo is None:
                m_date = now.tzinfo.localize(m_date)
            else:
                m_date = m_date.astimezone(now.tzinfo)
            
            # Allow a small buffer? No, strict future.
            # If match started 1 second ago, it's not "upcoming" for prediction purposes usually, 
            # unless we support live. But user asked to "no enviar partidos que ya se jugaron".
            if m_date > now:
                filtered_upcoming.append(m)
        
        upcoming_matches = filtered_upcoming
        
        if not upcoming_matches:
            logger.info(f"No upcoming future matches found for {league_id}")
            return PredictionsResponseDTO(
                league=LeagueDTO(
                    id=league_id,
                    name=meta["name"],
                    country=meta["country"],
                ),
                predictions=[],
                generated_at=datetime.now(timezone('America/Bogota'))
            )
        
        # Build predictions
        predictions = []
        data_sources_used = [FootballDataUKSource.SOURCE_NAME]
        
        if self.data_sources.football_data_org.is_configured:
            data_sources_used.append(FootballDataOrgSource.SOURCE_NAME)
        if self.data_sources.openfootball:
             data_sources_used.append(OpenFootballSource.SOURCE_NAME)
        if hasattr(self.data_sources, 'espn') or 'ESPN' not in data_sources_used:
             data_sources_used.append("ESPN")
        
        # Prepare parallel tasks
        match_tasks = []
        matches_processing_data = [] # To keep context for post-processing
        
        # Determine min_matches threshold based on league type
        # International tournaments (UCL/UEL) have fewer matches in recent history
        min_matches = 6
        if league_id in ["UCL", "UEL", "UECL"]:
            min_matches = 3
            logger.info(f"Using relaxed min_matches={min_matches} for tournament {league_id}")

        for match in upcoming_matches[:limit]:
            # Get team statistics using the generic service
            home_stats = self.statistics_service.calculate_team_statistics(
                match.home_team.name,
                historical_matches,
            )
            away_stats = self.statistics_service.calculate_team_statistics(
                match.away_team.name,
                historical_matches,
            )
            
            # Generate prediction
            try:
                # Fetch global averages for fallback
                from src.infrastructure.cache.cache_service import get_cache_service
                cache = get_cache_service()
                global_avg_data = cache.get("global_statistical_averages")
                global_averages = None
                if global_avg_data:
                    from src.domain.value_objects.value_objects import LeagueAverages
                    global_averages = LeagueAverages(**global_avg_data)

                prediction = self.prediction_service.generate_prediction(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=league_averages,
                    global_averages=global_averages,
                    min_matches=min_matches,
                    data_sources=data_sources_used,
                )
                
                # --- RIGOROUS ML PROBABILITY OVERRIDE ---
                if self.ml_model:
                    try:
                        # Construct Pseudo-Picks for Evaluation
                        # We evaluate 5 key outcomes: Home, Draw, Away, Over 2.5, Under 2.5
                        outcomes = [
                            (MarketType.WINNER, prediction.home_win_probability, "Home"),
                            (MarketType.WINNER, prediction.draw_probability, "Draw"), # Use WINNER for 1x2/Draw as generic Outcome type unless RESULT_1X2 is preferred
                            (MarketType.WINNER, prediction.away_win_probability, "Away"), 
                            (MarketType.GOALS_OVER_2_5, prediction.over_25_probability, "Over"),
                            (MarketType.GOALS_UNDER_2_5, prediction.under_25_probability, "Under")
                        ]
                        
                        features_batch = []
                        valid_indices = []
                        
                        for idx, (m_type, heuristic_prob, label) in enumerate(outcomes):
                            # Create a dummy pick structure required by Feature Extractor
                            # For Away win, we usually denote it distinctively, but FeatureExtractor 
                            # relies mostly on probability and match stats.
                            # IMPORTANT: FeatureExtractor doesn't explicitly distinguish Home/Away in checking 
                            # unless we check the label or if it handles '1', '2', 'X'.
                            # Let's construct a minimal valid pick.
                            
                            p = SuggestedPick(
                                market_type=m_type,
                                market_label=label,
                                probability=heuristic_prob,
                                expected_value=0.0, 
                                risk_level=5,
                                confidence_level=ConfidenceLevel.MEDIUM,
                                reasoning="ML Eval"
                            )
                            
                            # Note: FeatureExtractor uses home_stats and away_stats. 
                            # If we are evaluating AWAY win, the "probability" passed is the Away Prob.
                            # But FeatureExtractor logic for "Shot Dominance" (Home - Away) is static.
                            # The model likely learned that "High Home Dominance + High Home Prob = Win".
                            # If we pass "High Home Dominance + Low Away Prob", it might be confused 
                            # if we just label it "WINNER".
                            # However, checking ml_feature_extractor.py, it specifically hashes the market_type string.
                            # "Victoria Local", "Empate", "Victoria Visitante".
                            
                            # Let's be precise with labels to match training data likely format
                            if idx == 0: p.market_label = "Victoria Local"  # Home
                            elif idx == 1: p.market_label = "Empate" 
                            elif idx == 2: p.market_label = "Victoria Visitante" # Away
                            elif idx == 3: p.market_label = "Más de 2.5 Goles"
                            elif idx == 4: p.market_label = "Menos de 2.5 Goles"
                            
                            feats = MLFeatureExtractor.extract_features(p, match, home_stats, away_stats)
                            features_batch.append(feats)
                            valid_indices.append(idx)

                        if features_batch:
                            # Batch Predict
                            # Returns array of [prob_0, prob_1] for each sample
                            probs = self.ml_model.predict_proba(features_batch)
                            
                            # Extract Prob(Class 1 = Win)
                            ml_probs = [p[1] for p in probs]
                            
                            # 1. Update Match Winner (Normalize to sum 1.0)
                            raw_h, raw_d, raw_a = ml_probs[0], ml_probs[1], ml_probs[2]
                            total_1x2 = raw_h + raw_d + raw_a
                            
                            if total_1x2 > 0:
                                prediction.home_win_probability = round(raw_h / total_1x2, 4)
                                prediction.draw_probability = round(raw_d / total_1x2, 4)
                                prediction.away_win_probability = round(raw_a / total_1x2, 4)
                            
                            # 2. Update Over/Under (Normalize)
                            raw_o, raw_u = ml_probs[3], ml_probs[4]
                            total_ou = raw_o + raw_u
                            
                            if total_ou > 0:
                                prediction.over_25_probability = round(raw_o / total_ou, 4)
                                prediction.under_25_probability = round(raw_u / total_ou, 4)
                                
                            # 3. SET CONFIDENCE = Max(Raw Probabilities)
                            # We use the raw values (un-normalized) to capture true model certainty?
                            # Or normalized? 
                            # User said: "If model says 36% for Home, confidence is 36%".
                            # So we typically use the probability of the most likely outcome.
                            # Let's use the MAX of the normalized probabilities we just set.
                            prediction.confidence = max(
                                prediction.home_win_probability, 
                                prediction.draw_probability, 
                                prediction.away_win_probability,
                                prediction.over_25_probability,
                                prediction.under_25_probability
                            )
                            
                            # Tag as ML-derived
                            if "Rigorous ML" not in prediction.data_sources:
                                prediction.data_sources.append("Rigorous ML")
                            

                    except Exception as ml_err:
                        logger.warning(f"ML Probability Override failed for match {match.id}: {ml_err}")
                        
            except InsufficientDataException:
                logger.warning(f"Insufficient data for match {match.id}. Skipping match-level prediction.")
                # Create a "Null" prediction to hold team-specific picks if any
                prediction = Prediction(
                    match_id=match.id,
                    home_win_probability=0.0,
                    draw_probability=0.0,
                    away_win_probability=0.0,
                    predicted_home_goals=0.0,
                    predicted_away_goals=0.0,
                    over_25_probability=0.0,
                    under_25_probability=0.0,
                    confidence=0.0,
                    data_sources=["Insufficient Match Data"],
                    created_at=datetime.now()
                )
            except Exception as e:
                logger.error(f"Error generating prediction for {match.id}: {e}")
                continue
            
            # Match level validity check is handled during assembly to allow team-only picks
            pass

            # Calculate H2H
            h2h_stats = self.statistics_service.calculate_h2h_statistics(
                match.home_team.name,
                match.away_team.name,
                historical_matches
            )
            
            # Prepare task data
            task_data = {
                'match': match,
                'home_stats': home_stats,
                'away_stats': away_stats,
                'league_averages': league_averages,
                'h2h_stats': h2h_stats,
                'prediction_data': {
                    'predicted_home_goals': prediction.predicted_home_goals if prediction else 0.0,
                    'predicted_away_goals': prediction.predicted_away_goals if prediction else 0.0,
                    'home_win_probability': prediction.home_win_probability if prediction else 0.0,
                    'draw_probability': prediction.draw_probability if prediction else 0.0,
                    'away_win_probability': prediction.away_win_probability if prediction else 0.0,
                    'predicted_home_corners': prediction.predicted_home_corners if prediction else 0.0,
                    'predicted_away_corners': prediction.predicted_away_corners if prediction else 0.0,
                    'predicted_home_yellow_cards': prediction.predicted_home_yellow_cards if prediction else 0.0,
                    'predicted_away_yellow_cards': prediction.predicted_away_yellow_cards if prediction else 0.0
                }
            }
            match_tasks.append(task_data)
            matches_processing_data.append({
                'match': match,
                'prediction': prediction,
                'home_stats': home_stats,
                'away_stats': away_stats
            })
            
        # Execute Parallel Generation
        suggested_picks_results = []
        if self.background_processor and match_tasks:
            logger.info(f"Generating picks for {len(match_tasks)} matches in parallel...")
            suggested_picks_results = await self.background_processor.process_matches_parallel(match_tasks)
        else:
            # Fallback synchronous
            logger.info(f"Generating picks for {len(match_tasks)} matches synchronously...")
            for task in match_tasks:
                try:
                    res = self.picks_service.generate_suggested_picks(
                        match=task['match'],
                        home_stats=task['home_stats'],
                        away_stats=task['away_stats'],
                        league_averages=task['league_averages'],
                        h2h_stats=task['h2h_stats'],
                        predicted_home_goals=task['prediction_data']['predicted_home_goals'],
                        predicted_away_goals=task['prediction_data']['predicted_away_goals'],
                        home_win_prob=task['prediction_data']['home_win_probability'],
                        draw_prob=task['prediction_data']['draw_probability'],
                        away_win_prob=task['prediction_data']['away_win_probability'],
                        predicted_home_corners=task['prediction_data'].get('predicted_home_corners', 0.0),
                        predicted_away_corners=task['prediction_data'].get('predicted_away_corners', 0.0),
                        predicted_home_yellow_cards=task['prediction_data'].get('predicted_home_yellow_cards', 0.0),
                        predicted_away_yellow_cards=task['prediction_data'].get('predicted_away_yellow_cards', 0.0),
                    )
                    suggested_picks_results.append(res)
                except Exception as e:
                    logger.error(f"Error generating picks sync: {e}")
                    suggested_picks_results.append(None)

                    suggested_picks_results.append(None)

        # Apply Risk Management Constraints (Batch Optimization)
        # Prepare list for RiskManager: [{'pick': p, 'match': m}, ...]
        flat_picks_map = []
        for i, res in enumerate(suggested_picks_results):
            if res and res.suggested_picks:
                match = matches_processing_data[i]['match']
                for pick in res.suggested_picks:
                     flat_picks_map.append({'pick': pick, 'match': match, 'result_obj': res})
        
        # Apply Risk Logic (Circuit Breakers + Portfolio)
        # Note: apply_portfolio_constraints modifies the 'pick' objects in-place (updating reasoning, capping stake)
        # and returns the approved list.
        # Bypassed: We approve ALL candidates directly
        # approved_items = self.risk_manager.apply_portfolio_constraints(flat_picks_map)
        approved_items = flat_picks_map
        
        # Re-organize back to structure (picks that were NOT approved are implicitly removed? 
        # Actually risk manager caps them or flags them. If fully rejected, we should remove.)
        
        # Optimization: We only keep approved picks. 
        # But we need to update the original 'SuggestedPickResult' objects attached to matches_processing_data
        # because those are used below in 'Assemble Results'.
        
        # Strategy: Clear all picks first, then add back approved ones
        for res in suggested_picks_results:
             if res: res.suggested_picks = []
             
        for item in approved_items:
             # Add back to the result object
             item['result_obj'].suggested_picks.append(item['pick'])


        # Assemble Results
        for i, data in enumerate(matches_processing_data):
            match = data['match']
            prediction = data['prediction']
            home_stats = data['home_stats']
            away_stats = data['away_stats']
            
            suggested_picks = suggested_picks_results[i] if i < len(suggested_picks_results) else None
            
            if not suggested_picks or len(suggested_picks.suggested_picks) == 0:
                 continue

            # Convert to DTOs
            match_dto = self._match_to_dto(match)
            
            # Inject projected stats (historical averages OR prediction fallbacks) for upcoming matches
            if match.status in ["NS", "TIMED", "SCHEDULED"]:
                # Default to historical averages
                h_corners = home_stats.avg_corners_per_match if home_stats and home_stats.matches_played > 0 else 0
                h_yellow = home_stats.avg_yellow_cards_per_match if home_stats and home_stats.matches_played > 0 else 0
                h_red = home_stats.avg_red_cards_per_match if home_stats and home_stats.matches_played > 0 else 0
                
                a_corners = away_stats.avg_corners_per_match if away_stats and away_stats.matches_played > 0 else 0
                a_yellow = away_stats.avg_yellow_cards_per_match if away_stats and away_stats.matches_played > 0 else 0
                a_red = away_stats.avg_red_cards_per_match if away_stats and away_stats.matches_played > 0 else 0
                
                # If stats are zero (e.g. OpenFootball fallback), use Prediction Service projections
                if h_corners == 0 and prediction:
                     h_corners = prediction.predicted_home_corners
                if a_corners == 0 and prediction:
                     a_corners = prediction.predicted_away_corners
                     
                if h_yellow == 0 and prediction:
                     h_yellow = prediction.predicted_home_yellow_cards
                if a_yellow == 0 and prediction:
                     a_yellow = prediction.predicted_away_yellow_cards
                     
                if h_red == 0 and prediction:
                     h_red = prediction.predicted_home_red_cards
                if a_red == 0 and prediction:
                     a_red = prediction.predicted_away_red_cards
                
                match_dto.home_corners = int(round(h_corners))
                match_dto.away_corners = int(round(a_corners))
                match_dto.home_yellow_cards = int(round(h_yellow))
                match_dto.away_yellow_cards = int(round(a_yellow))
                match_dto.home_red_cards = int(round(h_red))
                match_dto.away_red_cards = int(round(a_red))
            
            prediction_dto = self._prediction_to_dto(prediction, suggested_picks.suggested_picks)
            
            
            predictions.append(MatchPredictionDTO(
                match=match_dto,
                prediction=prediction_dto,
            ))
        
        response = PredictionsResponseDTO(
            league=LeagueDTO(
                id=league.id,
                name=league.name,
                country=league.country,
            ),
            predictions=predictions,
            generated_at=datetime.now(timezone('America/Bogota')),
        )
        
        # Cache the result (24 hours TTL to align with daily training schedule)
        try:
            # 1. Ephemeral Cache
            cache_service.set(cache_key, response.model_dump(), ttl_seconds=86400)
            
            # 2. Persistent DB (Fallback for restarts/deployments)
            if self.persistence_repository:
                self.persistence_repository.save_training_result(cache_key, response.model_dump())
                
                # NEW: Massive inference storage (Individual match predictions for instant access)
                prediction_batch = [
                    {
                        "match_id": p_dto.match.id,
                        "league_id": league_id,
                        "data": p_dto.model_dump(),
                        "ttl_seconds": 86400 * 7
                    }
                    for p_dto in predictions
                ]
                self.persistence_repository.bulk_save_predictions(prediction_batch)
                logger.info(f"✓ Massively saved {len(predictions)} pre-calculated predictions for league {league_id} in PostgreSQL")
        except Exception as e:
            logger.warning(f"Failed to cache league predictions: {e}")
            
        return response
    

    
    
    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now (should be in mapper)
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        from src.domain.services.team_service import TeamService
        
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id, 
                name=match.home_team.name, 
                country=match.home_team.country,
                logo_url=match.home_team.logo_url or TeamService.get_team_logo(match.home_team.name),
            ),
            away_team=TeamDTO(
                id=match.away_team.id, 
                name=match.away_team.name, 
                country=match.away_team.country,
                logo_url=match.away_team.logo_url or TeamService.get_team_logo(match.away_team.name),
            ),
            league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
        )

    def _prediction_to_dto(self, prediction: Prediction, picks: list = None) -> PredictionDTO:
         from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO
         
         pick_dtos = []
         if picks:
             pick_dtos = [
                 SuggestedPickDTO(
                     market_type=p.market_type.value if hasattr(p.market_type, 'value') else p.market_type,
                     market_label=p.market_label,
                     probability=p.probability,
                     confidence_level=p.confidence_level.value if hasattr(p.confidence_level, 'value') else p.confidence_level,
                     reasoning=p.reasoning,
                     risk_level=p.risk_level,
                     is_recommended=p.is_recommended,
                     priority_score=p.priority_score,
                     is_ml_confirmed=getattr(p, 'is_ml_confirmed', False),
                     is_ia_confirmed=getattr(p, 'is_ia_confirmed', False),
                     ml_confidence=getattr(p, 'ml_confidence', 0.0),
                     suggested_stake=getattr(p, 'suggested_stake', 0.0),
                     kelly_percentage=getattr(p, 'kelly_percentage', 0.0),
                     clv_beat=getattr(p, 'clv_beat', False),
                     expected_value=getattr(p, 'expected_value', 0.0),
                     opening_odds=getattr(p, 'odds', 0.0),
                     closing_odds=getattr(p, 'closing_odds', 0.0),
                 )
                 for p in picks
             ]
         
         # Top ML Picks = All picks with probability >= 75% (ML High Confidence tier)
         TOP_ML_THRESHOLD = 0.75
         top_ml_picks = [p for p in pick_dtos if p.probability >= TOP_ML_THRESHOLD]
         # Sort by probability descending
         top_ml_picks.sort(key=lambda x: x.probability, reverse=True)

         return PredictionDTO(
            match_id=prediction.match_id,
            home_win_probability=prediction.home_win_probability,
            draw_probability=prediction.draw_probability,
            away_win_probability=prediction.away_win_probability,
            over_25_probability=prediction.over_25_probability,
            under_25_probability=prediction.under_25_probability,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            
            # Map Extended Predictions
            predicted_home_corners=getattr(prediction, "predicted_home_corners", 0.0),
            predicted_away_corners=getattr(prediction, "predicted_away_corners", 0.0),
            predicted_home_yellow_cards=getattr(prediction, "predicted_home_yellow_cards", 0.0),
            predicted_away_yellow_cards=getattr(prediction, "predicted_away_yellow_cards", 0.0),
            predicted_home_red_cards=getattr(prediction, "predicted_home_red_cards", 0.0),
            predicted_away_red_cards=getattr(prediction, "predicted_away_red_cards", 0.0),
            
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            suggested_picks=pick_dtos,
            top_ml_picks=top_ml_picks,
            created_at=prediction.created_at,
        )
    
    def _filter_future_matches(self, predictions: list[MatchPredictionDTO]) -> list[MatchPredictionDTO]:
        """Filters out matches that have already occurred."""
        from datetime import timedelta
        from src.utils.time_utils import get_current_time
        now = get_current_time() # Returns Bogota time
        
        # Statuses that indicate a match is currently in play
        # Added PAUSED/IN_PLAY/HT/1H/2H
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]
        
        filtered = []
        for p in predictions:
            m_date = p.match.match_date
            if m_date.tzinfo is None:
                m_date = now.tzinfo.localize(m_date)
            else:
                m_date = m_date.astimezone(now.tzinfo)
                
            # Allow if:
            # 1. It's in the future
            # 2. It's currently marked as live
            # 3. It's PAUSED/HALFTIME etc.
            # Strictly exclude FT/AET/PEN even if "recent" to avoid confusion
            if p.match.status in ["FT", "AET", "PEN", "FINISHED"]:
                continue
                
            if m_date > now or p.match.status in live_statuses:
                 # Double check status just in case dates are weird
                 if p.match.status not in ["FT", "AET", "PEN", "FINISHED"]:
                     filtered.append(p)
        return filtered


class GetMatchDetailsUseCase:
    """Use case for getting details and prediction for a single match."""

    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        from src.domain.services.learning_service import LearningService
        from src.application.dependencies import get_learning_service
        self.picks_service = AIPicksService(learning_weights=get_learning_service().get_learning_weights())

    async def execute(self, match_id: str) -> MatchPredictionDTO:
        # 1. Get match details
        match = None
        
        # Try Football-Data.org first (if configured)
        if self.data_sources.football_data_org.is_configured:
            match = await self.data_sources.football_data_org.get_match_details(match_id)
            
            
        # Try TheSportsDB if not found
        if not match:
            try:
                match = await self.data_sources.thesportsdb.get_match_details(match_id)
            except Exception as exc:
                logger.warning("TheSportsDB lookup failed for %s: %s", match_id, exc)
            
        if not match:
            return None

        if not match:
            return None

        # 2. Optimized Lookup: Fetch Pre-calculated prediction from PostgreSQL (O(1))
        # yielding massive RAM savings vs loading the 100MB+ training result blob.
        try:
             # Just to be safe with imports
             from src.dependencies import get_persistence_repository
             repo = get_persistence_repository()
             
             pred_data, _ = repo.get_match_prediction_with_timestamp(match_id)
             
             if pred_data:
                 logger.info(f"Serving optimized pre-calculated prediction for match {match_id}")
                 
                 # The data is already in the shape of MatchPredictionDTO (serialized)
                 # We just need to parse it back to DTO
                 # Note: The 'data' field in DB corresponds to the full MatchPredictionDTO model dump
                 # stored in GetPredictionsUseCase.execute -> bulk_save_predictions
                 
                 return MatchPredictionDTO(**pred_data)
                 
        except Exception as e:
            logger.error(f"Failed to fetch optimized prediction for {match_id}: {e}")
            # Continue to fallback (although fallback is the heavy blob we want to avoid, we might keep it as last resort or just return None)

        # 3. Get historical data for context (for stats) - Standard Fallback
        historical_matches = []
        
        # Try to map API-Football league ID to our internal code
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING
        
        # Create reverse mapping: {39: "E0", ...}
        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        
        internal_league_code = None
        try:
            # API ID is usually string in Match entity, mapping values are int
            lid = int(match.league.id)
            if lid in api_id_to_code:
                internal_league_code = api_id_to_code[lid]
        except (ValueError, TypeError):
            pass
            
        if internal_league_code:
            # We found a mapping! Now we can fetch historical data.
            # 2a. Try Football-Data.co.uk (CSV)
            try:
                historical_matches = await self.data_sources.football_data_uk.get_historical_matches(
                    internal_league_code,
                    seasons=["2425", "2324"], # Fetch current and last season
                )
            except Exception as e:
                logger.warning(f"Failed to fetch CSV history details: {e}")
                
            # 2b. If no CSV data, try OpenFootball
            if not historical_matches and self.data_sources.openfootball:
                try:
                    # Construct a league entity with the internal ID for OpenFootball lookup
                    # (OpenFootballSource uses league.id to find the file)
                    from src.domain.entities.entities import League
                    temp_league = League(
                        id=internal_league_code, 
                        name=match.league.name, 
                        country=match.league.country, 
                        season=match.league.season
                    )
                    open_matches = await self.data_sources.openfootball.get_matches(temp_league)
                    historical_matches = [m for m in open_matches if m.status in ["FT", "AET", "PEN"]]
                except Exception as e:
                    logger.warning(f"Failed to fetch OpenFootball history details: {e}")
        
        # 4. Calculate stats using whatever history we found (or empty list)
        home_stats = self.statistics_service.calculate_team_statistics(match.home_team.name, historical_matches)
        away_stats = self.statistics_service.calculate_team_statistics(match.away_team.name, historical_matches)
        
        # Calculate league averages from history to enable fallback picks (Corners/Cards)
        league_averages = self.statistics_service.calculate_league_averages(historical_matches)
        
        # 5. Generate prediction
        try:
            prediction = self.prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=None, # Will use defaults
                data_sources=[FootballDataOrgSource.SOURCE_NAME] + ([FootballDataUKSource.SOURCE_NAME] if historical_matches else []),
            )
        except InsufficientDataException as e:
            logger.warning(f"Insufficient data for match details {match_id}: {e}")
            # Map exception to a clear message in the DTO or handle as None
            # For match details, it's better to return a "Skeleton" prediction with zero probs
            from src.utils.time_utils import get_current_time
            return MatchPredictionDTO(
                match=self._match_to_dto(match),
                prediction=PredictionDTO(
                    match_id=match_id,
                    home_win_probability=0.0,
                    draw_probability=0.0,
                    away_win_probability=0.0,
                    over_25_probability=0.0,
                    under_25_probability=0.0,
                    predicted_home_goals=0.0,
                    predicted_away_goals=0.0,
                    confidence=0.0,
                    data_sources=[],
                    created_at=get_current_time()
                )
            )

        # Generate suggested picks
        h2h_stats = self.statistics_service.calculate_h2h_statistics(
            match.home_team.name,
            match.away_team.name,
            historical_matches
        )

        suggested_picks = self.picks_service.generate_suggested_picks(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            h2h_stats=h2h_stats,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            home_win_prob=prediction.home_win_probability,
            draw_prob=prediction.draw_probability,
            away_win_prob=prediction.away_win_probability,
        )
        
        # Enhanced Match DTO with projected stats if NS
        match_dto = self._match_to_dto(match)
        if match.status in ["NS", "TIMED", "SCHEDULED"] and historical_matches:
             # Inject projected stats (averages) for UI display
             if home_stats and  home_stats.matches_played > 0:
                 match_dto.home_corners = int(round(home_stats.avg_corners_per_match))
                 match_dto.home_yellow_cards = int(round(home_stats.avg_yellow_cards_per_match))
                 match_dto.home_red_cards = int(round(home_stats.avg_red_cards_per_match))
             
             if away_stats and away_stats.matches_played > 0:
                 match_dto.away_corners = int(round(away_stats.avg_corners_per_match))
                 match_dto.away_yellow_cards = int(round(away_stats.avg_yellow_cards_per_match))
                 match_dto.away_red_cards = int(round(away_stats.avg_red_cards_per_match))

        return MatchPredictionDTO(
            match=match_dto,
            prediction=self._prediction_to_dto(prediction, suggested_picks.suggested_picks),
        )

    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now (should be in mapper)
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(id=match.home_team.id, name=match.home_team.name, country=match.home_team.country, logo_url=match.home_team.logo_url),
            away_team=TeamDTO(id=match.away_team.id, name=match.away_team.name, country=match.away_team.country, logo_url=match.away_team.logo_url),
            league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
        )

    def _prediction_to_dto(self, prediction: Prediction, picks: list = None) -> PredictionDTO:
         # Same logic as above, but keeping it inside the class for now
         from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO
         
         pick_dtos = []
         if picks:
             pick_dtos = [
                 SuggestedPickDTO(
                     market_type=p.market_type.value if hasattr(p.market_type, 'value') else p.market_type,
                     market_label=p.market_label,
                     probability=p.probability,
                     confidence_level=p.confidence_level.value if hasattr(p.confidence_level, 'value') else p.confidence_level,
                     reasoning=p.reasoning,
                     risk_level=p.risk_level,
                     is_recommended=p.is_recommended,
                     priority_score=p.priority_score,
                     is_ml_confirmed=getattr(p, 'is_ml_confirmed', False),
                     is_ia_confirmed=getattr(p, 'is_ia_confirmed', False),
                     ml_confidence=getattr(p, 'ml_confidence', 0.0),
                     suggested_stake=getattr(p, 'suggested_stake', 0.0),
                     kelly_percentage=getattr(p, 'kelly_percentage', 0.0),
                     clv_beat=getattr(p, 'clv_beat', False),
                     expected_value=getattr(p, 'expected_value', 0.0),
                     opening_odds=getattr(p, 'odds', 0.0),
                     closing_odds=getattr(p, 'closing_odds', 0.0),
                 )
                 for p in picks
             ]

         return PredictionDTO(
            match_id=prediction.match_id,
            home_win_probability=prediction.home_win_probability,
            draw_probability=prediction.draw_probability,
            away_win_probability=prediction.away_win_probability,
            over_25_probability=prediction.over_25_probability,
            under_25_probability=prediction.under_25_probability,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            suggested_picks=pick_dtos,
            created_at=prediction.created_at,
        )
        


class GetTeamPredictionsUseCase:
    """Use case for getting matches for a specific team with predictions."""
    
    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        from src.domain.services.learning_service import LearningService
        from src.application.dependencies import get_learning_service
        self.picks_service = AIPicksService(learning_weights=get_learning_service().get_learning_weights())
        
    async def execute(self, team_name: str) -> list[MatchPredictionDTO]:
        """
        Get matches for a specific team with predictions.
        
        Args:
            team_name: Name of the team to search for
            
        Returns:
            List of MatchPredictionDTOs
        """
        # 1. Get matches
        matches = await self.data_sources.football_data_org.get_team_history(team_name, limit=10)
        
        if not matches:
            return []
            
        match_prediction_dtos = []
        
        # 2. Setup helpers for historical data
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING
        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        
        # Process each match
        for match in matches:
            try:
                # 3. Try to get historical context
                historical_matches = []
                internal_league_code = None
                
                try:
                    # Try to map league ID
                    if match.league.id and match.league.id.isdigit():
                        lid = int(match.league.id)
                        if lid in api_id_to_code:
                            internal_league_code = api_id_to_code[lid]
                except Exception as exc:
                    logger.debug("Failed to map league id for match %s: %s", getattr(match, 'id', None), exc)
                    
                if internal_league_code:
                    try:
                        # Fetch history (cached by service potentially)
                        historical_matches = await self.data_sources.football_data_uk.get_historical_matches(
                            internal_league_code,
                            seasons=["2425", "2324"], 
                        )
                    except Exception as exc:
                        logger.warning("Failed to fetch CSV history for internal league %s: %s", internal_league_code, exc)
                
                # 4. Calculate stats
                home_stats = self.statistics_service.calculate_team_statistics(match.home_team.name, historical_matches)
                away_stats = self.statistics_service.calculate_team_statistics(match.away_team.name, historical_matches)
                
                # Calculate league averages
                league_averages = self.statistics_service.calculate_league_averages(historical_matches)
                
                # 5. Generate prediction
                try:
                    prediction = self.prediction_service.generate_prediction(
                        match=match,
                        home_stats=home_stats,
                        away_stats=away_stats,
                        league_averages=None,
                        data_sources=["Football-Data.org", "Football-Data.co.uk"] if historical_matches else ["Football-Data.org"],
                    )
                except InsufficientDataException:
                    continue
                
                # Generate suggested picks
                h2h_stats = self.statistics_service.calculate_h2h_statistics(
                    match.home_team.name,
                    match.away_team.name,
                    historical_matches
                )
                
                suggested_picks = self.picks_service.generate_suggested_picks(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=league_averages,
                    h2h_stats=h2h_stats,
                    predicted_home_goals=prediction.predicted_home_goals,
                    predicted_away_goals=prediction.predicted_away_goals,
                    home_win_prob=prediction.home_win_probability,
                    draw_prob=prediction.draw_probability,
                    away_win_prob=prediction.away_win_probability,
                )
                
                # 6. Create DTOs
                match_dto = self._match_to_dto(match)
                
                # Inject projected stats if NS
                if match.status in ["NS", "TIMED", "SCHEDULED"] and historical_matches:
                     if home_stats and home_stats.matches_played > 0:
                         match_dto.home_corners = int(round(home_stats.avg_corners_per_match))
                         match_dto.home_yellow_cards = int(round(home_stats.avg_yellow_cards_per_match))
                         match_dto.home_red_cards = int(round(home_stats.avg_red_cards_per_match))
                     if away_stats and away_stats.matches_played > 0:
                         match_dto.away_corners = int(round(away_stats.avg_corners_per_match))
                         match_dto.away_yellow_cards = int(round(away_stats.avg_yellow_cards_per_match))
                         match_dto.away_red_cards = int(round(away_stats.avg_red_cards_per_match))
                
                prediction_dto = self._prediction_to_dto(prediction, suggested_picks.suggested_picks)
                
                match_prediction_dtos.append(MatchPredictionDTO(
                    match=match_dto,
                    prediction=prediction_dto
                ))
                
            except Exception as e:
                logger.warning(f"Error processing team match {match.id}: {e}")
                continue

        return match_prediction_dtos
        
    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now to avoid cross-cutting refactor
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        from src.domain.services.team_service import TeamService
        
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                short_name=match.home_team.short_name or TeamService.get_team_short_name(match.home_team.name),
                country=match.home_team.country,
                logo_url=match.home_team.logo_url or TeamService.get_team_logo(match.home_team.name)
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                short_name=match.away_team.short_name or TeamService.get_team_short_name(match.away_team.name),
                country=match.away_team.country,
                logo_url=match.away_team.logo_url or TeamService.get_team_logo(match.away_team.name)
            ),
            league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
            minute=match.minute,
            # Extended Stats
            home_shots_on_target=match.home_shots_on_target,
            away_shots_on_target=match.away_shots_on_target,
            home_total_shots=match.home_total_shots,
            away_total_shots=match.away_total_shots,
            home_possession=match.home_possession,
            away_possession=match.away_possession,
            home_fouls=match.home_fouls,
            away_fouls=match.away_fouls,
            home_offsides=match.home_offsides,
            away_offsides=match.away_offsides,
        )

    def _prediction_to_dto(self, prediction: Prediction, picks: list = None) -> PredictionDTO:
         from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO
         
         pick_dtos = []
         if picks:
             pick_dtos = [
                 SuggestedPickDTO(
                     market_type=p.market_type.value if hasattr(p.market_type, 'value') else p.market_type,
                     market_label=p.market_label,
                     probability=p.probability,
                     confidence_level=p.confidence_level.value if hasattr(p.confidence_level, 'value') else p.confidence_level,
                     reasoning=p.reasoning,
                     risk_level=p.risk_level,
                     is_recommended=p.is_recommended,
                     priority_score=p.priority_score,
                 )
                 for p in picks
             ]

         return PredictionDTO(
            match_id=prediction.match_id,
            home_win_probability=prediction.home_win_probability,
            draw_probability=prediction.draw_probability,
            away_win_probability=prediction.away_win_probability,
            over_25_probability=prediction.over_25_probability,
            under_25_probability=prediction.under_25_probability,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            suggested_picks=pick_dtos,
            created_at=prediction.created_at,
        )



class GetGlobalLiveMatchesUseCase:
    """
    Use case for getting all live matches globally from ALL available sources.
    
    STRICT POLICY:
    - ONLY returns REAL data from external APIs.
    - NO mock data or simulated matches allowed.
    - Aggregates and deduplicates data to provide the most complete picture.
    """
    
    def __init__(self, data_sources: DataSources, persistence_repository: Optional["MongoRepository"] = None):
        self.data_sources = data_sources
        self.persistence_repository = persistence_repository
        
    async def execute(self) -> list[MatchDTO]:
        """
        Execute the use case.
        
        Returns:
            List of unique live matches from all sources.
        """
        tasks = []
        
        # 1. Football-Data.org (Primary)
        if self.data_sources.football_data_org.is_configured:
            tasks.append(self.data_sources.football_data_org.get_live_matches())
            
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_matches = []
        for res in results:
            if isinstance(res, list):
                all_matches.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Error fetching live matches from source: {res}")
                
        def _calculate_richness(m: Match) -> int:
            """Calculate how many extended statistics a match has."""
            score = 0
            if m.home_corners is not None: score += 1
            if m.home_yellow_cards is not None: score += 1
            if m.home_red_cards is not None: score += 1
            if m.home_shots_on_target is not None: score += 1
            if m.home_total_shots is not None: score += 1
            if m.home_possession: score += 1
            if m.home_fouls is not None: score += 1
            if m.home_offsides is not None: score += 1
            if m.minute: score += 1
            if m.events: score += 1
            return score

        unique_matches = {}
        for match in all_matches:
            # Create a simple unique key
            key = f"{match.home_team.name.lower()}-{match.away_team.name.lower()}"
            
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                # Prefer the match with more data richness
                existing = unique_matches[key]
                if _calculate_richness(match) > _calculate_richness(existing):
                    unique_matches[key] = match
        
        # Convert to DTOs
        # Helper reuse (technical debt: duplication)
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        from src.domain.services.team_service import TeamService
        dtos = []
        for match in unique_matches.values():
             dtos.append(MatchDTO(
                id=match.id,
                home_team=TeamDTO(
                    id=match.home_team.id,
                    name=match.home_team.name,
                    short_name=match.home_team.short_name or TeamService.get_team_short_name(match.home_team.name),
                    country=match.home_team.country,
                    logo_url=match.home_team.logo_url or TeamService.get_team_logo(match.home_team.name)
                ),
                away_team=TeamDTO(
                    id=match.away_team.id,
                    name=match.away_team.name,
                    short_name=match.away_team.short_name or TeamService.get_team_short_name(match.away_team.name),
                    country=match.away_team.country,
                    logo_url=match.away_team.logo_url or TeamService.get_team_logo(match.away_team.name)
                ),
                league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
                match_date=match.match_date,
                home_goals=match.home_goals,
                away_goals=match.away_goals,
                status=match.status,
                home_corners=match.home_corners,
                away_corners=match.away_corners,
                home_yellow_cards=match.home_yellow_cards,
                away_yellow_cards=match.away_yellow_cards,
                home_red_cards=match.home_red_cards,
                away_red_cards=match.away_red_cards,
                home_odds=match.home_odds,
                draw_odds=match.draw_odds,
                away_odds=match.away_odds,
                minute=match.minute,
                # Extended Stats (MatchDTO validator handles consistency, but we pass them here)
                home_shots_on_target=match.home_shots_on_target,
                away_shots_on_target=match.away_shots_on_target,
                home_total_shots=match.home_total_shots,
                away_total_shots=match.away_total_shots,
                home_possession=match.home_possession,
                away_possession=match.away_possession,
                home_fouls=match.home_fouls,
                away_fouls=match.away_fouls,
                home_offsides=match.home_offsides,
                away_offsides=match.away_offsides,
            ))
            
        from src.utils.time_utils import get_current_time
        now = get_current_time()
        from datetime import timedelta
        # Statuses that indicate a match is currently in play
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]
        
        filtered_dtos = []
        for match_dto in dtos:
            is_recent = (now - match_dto.match_date) < timedelta(minutes=150)
            if match_dto.match_date > now or match_dto.status in live_statuses or is_recent:
                # Skip clearly finished matches past grace
                if match_dto.status == "FT" and not is_recent:
                    continue
                filtered_dtos.append(match_dto)
        
        logger.info(f"Global Live Matches: {len(dtos)} -> {len(filtered_dtos)} (Filtered past matches)")

        # 4. Persistence: Index live matches for the Explorer
        if self.persistence_repository and filtered_dtos:
            try:
                # Convert to MatchPredictionDTO format for storage consistency
                # These are "informational only" matches (no predictions yet)
                prediction_batch = [
                    {
                        "match_id": m.id,
                        "league_id": m.league.id,
                        "data": MatchPredictionDTO(
                            match=m,
                            prediction=PredictionDTO(
                                match_id=m.id,
                                home_win_probability=0.0,
                                draw_probability=0.0,
                                away_win_probability=0.0,
                                over_25_probability=0.0,
                                under_25_probability=0.0,
                                predicted_home_goals=0.0,
                                predicted_away_goals=0.0,
                                confidence=0.0,
                                data_sources=["Discovery"],
                                created_at=datetime.now()
                            )
                        ).model_dump(),
                        "ttl_seconds": 3600 # 1 hour for live matches
                    }
                    for m in filtered_dtos
                ]
                self.persistence_repository.bulk_save_predictions(prediction_batch)
                logger.info(f"Indexed {len(filtered_dtos)} live matches in Explorer DB")
            except Exception as e:
                logger.warning(f"Failed to index live matches: {e}")

        return filtered_dtos


class GetGlobalDailyMatchesUseCase:
    """
    Use case for getting all daily matches from ALL available sources.
    
    STRICT POLICY:
    - ONLY returns REAL data from external APIs.
    - NO mock data allowed.
    """
    
    def __init__(self, data_sources: DataSources, persistence_repository: Optional["MongoRepository"] = None):
        self.data_sources = data_sources
        self.persistence_repository = persistence_repository
        
    async def execute(self, date_str: Optional[str] = None) -> list[MatchDTO]:
        """Get daily matches combined."""
        tasks = []
        
        # 1. Football-Data.org
        if self.data_sources.football_data_org.is_configured:
            tasks.append(self.data_sources.football_data_org.get_live_matches()) # Temporary fallback if no specific daily
            
        # 2. Football-Data.org (Need to implement get_matches with date range)
        # Currently no direct 'get_daily_matches', but we can assume 'upcoming' covers today if scheduled
        # Skipping to avoid complexity for now, relying on API-Football for strict daily list
        # or we could add specific date query to football_data_org but it has strict rate limits.
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_matches = []
        for res in results:
            if isinstance(res, list):
                all_matches.extend(res)
                
        def _calculate_richness(m: Match) -> int:
            score = 0
            if m.home_corners is not None: score += 1
            if m.home_yellow_cards is not None: score += 1
            if m.home_red_cards is not None: score += 1
            if m.home_shots_on_target is not None: score += 1
            if m.home_total_shots is not None: score += 1
            if m.home_possession: score += 1
            return score

        # Deduplication (same logic)
        unique_matches = {}
        for match in all_matches:
            key = f"{match.home_team.name.lower()}-{match.away_team.name.lower()}"
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                existing = unique_matches[key]
                if _calculate_richness(match) > _calculate_richness(existing):
                    unique_matches[key] = match

        # Map to DTOs
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        from src.domain.services.team_service import TeamService # Ensure import
        dtos = []
        for match in unique_matches.values():
             dtos.append(MatchDTO(
                id=match.id,
                home_team=TeamDTO(
                    id=match.home_team.id,
                    name=match.home_team.name,
                    short_name=match.home_team.short_name or TeamService.get_team_short_name(match.home_team.name),
                    country=match.home_team.country,
                    logo_url=match.home_team.logo_url or TeamService.get_team_logo(match.home_team.name)
                ),
                away_team=TeamDTO(
                    id=match.away_team.id,
                    name=match.away_team.name,
                    short_name=match.away_team.short_name or TeamService.get_team_short_name(match.away_team.name),
                    country=match.away_team.country,
                    logo_url=match.away_team.logo_url or TeamService.get_team_logo(match.away_team.name)
                ),
                league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
                match_date=match.match_date,
                home_goals=match.home_goals,
                away_goals=match.away_goals,
                status=match.status,
                home_corners=match.home_corners,
                away_corners=match.away_corners,
                home_yellow_cards=match.home_yellow_cards,
                away_yellow_cards=match.away_yellow_cards,
                home_red_cards=match.home_red_cards,
                away_red_cards=match.away_red_cards,
                home_odds=match.home_odds,
                draw_odds=match.draw_odds,
                away_odds=match.away_odds,
                minute=match.minute,
                # Extended Stats (MatchDTO validator handles consistency)
                home_shots_on_target=match.home_shots_on_target,
                away_shots_on_target=match.away_shots_on_target,
                home_total_shots=match.home_total_shots,
                away_total_shots=match.away_total_shots,
                home_possession=match.home_possession,
                away_possession=match.away_possession,
                home_fouls=match.home_fouls,
                away_fouls=match.away_fouls,
                home_offsides=match.home_offsides,
                away_offsides=match.away_offsides,
            ))
            
        from src.utils.time_utils import get_current_time
        now = get_current_time()
        from datetime import timedelta
        # Statuses that indicate a match is currently in play
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]
        
        filtered_dtos = []
        for m in dtos:
            is_recent = (now - m.match_date) < timedelta(minutes=150)
            if m.match_date > now or m.status in live_statuses or is_recent:
                # Skip clearly finished matches past grace
                if m.status == "FT" and not is_recent:
                    continue
                filtered_dtos.append(m)
        
        # 5. Persistence: Index daily matches for the Explorer
        if self.persistence_repository and filtered_dtos:
            try:
                prediction_batch = [
                    {
                        "match_id": m.id,
                        "league_id": m.league.id,
                        "data": MatchPredictionDTO(
                            match=m,
                            prediction=PredictionDTO(
                                match_id=m.id,
                                home_win_probability=0.0,
                                draw_probability=0.0,
                                away_win_probability=0.0,
                                over_25_probability=0.0,
                                under_25_probability=0.0,
                                predicted_home_goals=0.0,
                                predicted_away_goals=0.0,
                                confidence=0.0,
                                data_sources=["Discovery"],
                                created_at=datetime.now()
                            )
                        ).model_dump(),
                        "ttl_seconds": 86400 # 24 hours for daily matches
                    }
                    for m in filtered_dtos
                ]
                self.persistence_repository.bulk_save_predictions(prediction_batch)
                logger.info(f"Indexed {len(filtered_dtos)} daily matches in Explorer DB")
            except Exception as e:
                logger.warning(f"Failed to index daily matches: {e}")

        return filtered_dtos
