import os
import sys

# Add backend to path (assuming run from project root)
sys.path.append(os.path.join(os.getcwd(), "backend"))  # To find 'src' as a module
sys.path.append(os.getcwd())

import asyncio  # noqa: E402
import logging  # noqa: E402
import time  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402

import joblib  # noqa: E402
import numpy as np  # noqa: E402
from src.application.dtos.dtos import (  # noqa: E402
    LeagueDTO,
    MatchDTO,
    MatchPredictionDTO,
    PredictionDTO,
    SuggestedPickDTO,
    TeamDTO,
)
from src.core.constants import DEFAULT_LEAGUES  # noqa: E402
from src.core.model_artifacts import cleanup_model_artifacts  # noqa: E402
from src.domain.services.learning_service import LearningService  # noqa: E402
from src.domain.services.ml_feature_extractor import MLFeatureExtractor  # noqa: E402
from src.domain.services.pick_resolution_service import (  # noqa: E402
    PickResolutionService,
)
from src.domain.services.picks_service import PicksService  # noqa: E402
from src.domain.services.prediction_service import PredictionService  # noqa: E402
from src.domain.services.statistics_service import StatisticsService  # noqa: E402
from src.domain.services.team_service import TeamService  # noqa: E402

# Import Services

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TrainPerLeague")

# Global Service Instances (for worker processes)
_prediction_service = None
_picks_service = None
_statistics_service = None
_feature_extractor = None
_resolution_service = None


def init_worker(weights):
    """Initialize services in the worker process"""
    global _prediction_service
    global _picks_service
    global _statistics_service
    global _feature_extractor
    global _resolution_service

    _statistics_service = StatisticsService()
    _prediction_service = (
        PredictionService()
    )  # learning_service not needed for pure prediction generation?
    # Actually PredictionService might need simple init.

    _picks_service = PicksService(learning_weights=weights)
    _feature_extractor = MLFeatureExtractor()
    _resolution_service = PickResolutionService()


def parse_args(argv: Optional[List[str]] = None):
    """Parse CLI arguments and return Namespace.

    Kept as a small wrapper to make parsing testable.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Train ML models per league")
    parser.add_argument(
        "--days", type=int, default=550, help="Days back to fetch data for"
    )
    parser.add_argument(
        "--league", type=str, help="Specific league ID to train (optional)"
    )
    parser.add_argument(
        "--n-jobs", type=int, default=-1, help="Number of parallel jobs"
    )
    parser.add_argument(
        "--force-retrain-per-league",
        action="store_true",
        help="Force retraining per league",
    )
    parser.add_argument("--no-timeout", action="store_true", help="Disable timeout")

    return parser.parse_args(argv)


def clear_stale_predictions(repo: Any, league_ids: Optional[List[str]] = None) -> bool:
    """Clear stale predictions from persistence repository and log result."""
    success = repo.clear_all_predictions(league_ids=league_ids)
    if success:
        target = f"for leagues: {league_ids}" if league_ids else "for ALL leagues"
        logger.info(
            f"🗑️  Cleared old match predictions from database {target} to force regeneration."
        )
    else:
        logger.warning("⚠️  Failed to clear old predictions. Stale data might persist.")
    return success


def group_matches_by_league(matches: List[Any]) -> Dict[str, List[Any]]:
    """Group a list of matches by league id, preserving chronological order."""
    matches_by_league: Dict[str, List[Any]] = {}
    for m in matches:
        matches_by_league.setdefault(m.league.id, []).append(m)
    return matches_by_league


def build_training_tasks(
    league_matches: List[Any],
    stats_service: StatisticsService,
    learning_service: LearningService,
    league_avgs: Any,
) -> (Dict[str, Any], List[Any]):
    """Build rolling team stats cache and training tasks list for a league."""
    team_stats_cache: Dict[str, Any] = {}
    empty_stats = stats_service.create_empty_stats_dict()
    training_tasks: List[Any] = []

    weights = learning_service.get_learning_weights()

    for match in league_matches:
        if match.home_goals is None or match.away_goals is None:
            continue

        h_name = stats_service.normalize_team_name(match.home_team.name)
        a_name = stats_service.normalize_team_name(match.away_team.name)

        # Snapshot state BEFORE match
        raw_home = team_stats_cache.get(h_name, empty_stats).copy()
        raw_away = team_stats_cache.get(a_name, empty_stats).copy()

        # Init if new
        if h_name not in team_stats_cache:
            team_stats_cache[h_name] = raw_home
        if a_name not in team_stats_cache:
            team_stats_cache[a_name] = raw_away

        # Warmup check (> 3 matches)
        if raw_home["matches_played"] >= 3 and raw_away["matches_played"] >= 3:
            training_tasks.append(
                (match, raw_home, raw_away, league_avgs, None, weights)
            )

        # Update State
        stats_service.update_team_stats_dict(
            team_stats_cache[h_name], match, is_home=True
        )
        stats_service.update_team_stats_dict(
            team_stats_cache[a_name], match, is_home=False
        )

    return team_stats_cache, training_tasks


def extract_features_from_tasks(training_tasks: List[Any], args: Any):
    """Run feature extraction in parallel and return feature/target arrays."""
    x = []
    y_corners = []
    y_cards = []
    y_outcome = []  # 0=Draw, 1=Home, 2=Away

    try:
        results = joblib.Parallel(n_jobs=args.n_jobs, batch_size=50)(
            joblib.delayed(process_match_task)(task) for task in training_tasks
        )

        for feats, targets in results:
            x.append(feats)
            y_corners.append(targets["total_corners"])
            y_cards.append(targets["total_cards"])

            outcome = 0
            if targets["home_win"]:
                outcome = 1
            elif targets["away_win"]:
                outcome = 2
            y_outcome.append(outcome)

    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        return [], [], [], []

    return x, y_corners, y_cards, y_outcome


async def generate_league_predictions(
    league_id: str,
    league_matches: List[Any],
    team_stats_cache: Dict[str, Any],
    league_avgs: Any,
    aggregator: Any,
    stats_service: StatisticsService,
    pred_service: PredictionService,
    picks_service: Any,
    models_bundle: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Generate predictions for upcoming matches of a given league.

    This was previously nested in `main()`; lifted to module-level and
    receives explicit dependencies to make testing and reasoning easier.
    """
    try:
        upcoming = await aggregator.get_upcoming_matches(league_id, limit=50)
        if not upcoming:
            return []

        logger.info(
            "🔮 Generating predictions for %d upcoming matches "
            "using TRAINED MODELS...",
            len(upcoming),
        )

        batch_data: List[Dict[str, Any]] = []

        for match in upcoming:
            # Get Stats from Cache
            h_name = stats_service.normalize_team_name(match.home_team.name)
            a_name = stats_service.normalize_team_name(match.away_team.name)

            # Use current state of stats (after all history processed)
            raw_home = team_stats_cache.get(
                h_name, stats_service.create_empty_stats_dict()
            )
            raw_away = team_stats_cache.get(
                a_name, stats_service.create_empty_stats_dict()
            )

            home_stats = stats_service.convert_to_domain_stats(h_name, raw_home)
            away_stats = stats_service.convert_to_domain_stats(a_name, raw_away)

            # Calculate H2H
            h2h_stats = stats_service.calculate_h2h_statistics(
                h_name, a_name, league_matches
            )

            try:
                # Generate Prediction with IN-MEMORY MODELS
                prediction = pred_service.generate_prediction(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=league_avgs,
                    active_models=models_bundle,
                )

                # Generate Picks Integration
                winner_model = models_bundle.get("winner") if models_bundle else None

                picks_container = picks_service.generate_suggested_picks(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=league_avgs,
                    h2h_stats=h2h_stats,
                    predicted_home_goals=prediction.predicted_home_goals,
                    predicted_away_goals=prediction.predicted_away_goals,
                    home_win_prob=prediction.home_win_probability,
                    draw_prob=prediction.draw_probability,
                    away_win_prob=prediction.away_win_probability,
                    predicted_home_corners=prediction.predicted_home_corners,
                    predicted_away_corners=prediction.predicted_away_corners,
                    predicted_home_yellow_cards=prediction.predicted_home_yellow_cards,
                    predicted_away_yellow_cards=prediction.predicted_away_yellow_cards,
                    ml_model=winner_model,
                )

                # Map Domain Picks to DTOs
                pick_dtos = []
                for p in picks_container.suggested_picks:
                    pick_dtos.append(
                        SuggestedPickDTO(
                            market_type=p.market_type.value
                            if hasattr(p.market_type, "value")
                            else str(p.market_type),
                            market_label=p.market_label,
                            probability=p.probability,
                            odds=p.odds,
                            confidence_level=p.confidence_level.value
                            if hasattr(p.confidence_level, "value")
                            else str(p.confidence_level),
                            reasoning=p.reasoning,
                            priority_score=p.priority_score,
                            is_recommended=p.is_recommended,
                            expected_value=p.expected_value,
                            risk_level=p.risk_level.value
                            if hasattr(p.risk_level, "value")
                            else str(p.risk_level),
                        )
                    )

                # Manual DTO mapping
                m_dto = MatchDTO(
                    id=match.id,
                    home_team=TeamDTO(
                        id=match.home_team.id,
                        name=match.home_team.name,
                        country=match.home_team.country,
                        logo_url=match.home_team.logo_url
                        or TeamService.get_team_logo(match.home_team.name),
                    ),
                    away_team=TeamDTO(
                        id=match.away_team.id,
                        name=match.away_team.name,
                        country=match.away_team.country,
                        logo_url=match.away_team.logo_url
                        or TeamService.get_team_logo(match.away_team.name),
                    ),
                    league=LeagueDTO(
                        id=match.league.id,
                        name=match.league.name,
                        country=match.league.country,
                        season=match.league.season,
                    ),
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

                p_dto = PredictionDTO(
                    match_id=prediction.match_id,
                    home_win_probability=prediction.home_win_probability,
                    draw_probability=prediction.draw_probability,
                    away_win_probability=prediction.away_win_probability,
                    over_25_probability=prediction.over_25_probability,
                    under_25_probability=prediction.under_25_probability,
                    predicted_home_goals=prediction.predicted_home_goals,
                    predicted_away_goals=prediction.predicted_away_goals,
                    predicted_home_corners=prediction.predicted_home_corners,
                    predicted_away_corners=prediction.predicted_away_corners,
                    predicted_home_yellow_cards=prediction.predicted_home_yellow_cards,
                    predicted_away_yellow_cards=prediction.predicted_away_yellow_cards,
                    confidence=prediction.confidence,
                    display_confidence=prediction.confidence,
                    is_value_bet=prediction.is_value_bet,
                    expected_value=prediction.expected_value,
                    data_updated_at=prediction.data_updated_at,
                    data_sources=prediction.data_sources,
                    created_at=prediction.created_at,
                    recommended_bet=prediction.recommended_bet,
                    over_under_recommendation=prediction.over_under_recommendation,
                    suggested_picks=pick_dtos,
                    model_metadata={
                        "model_version": os.getenv("MODEL_VERSION", "unknown"),
                        "training_run": os.getenv("TRAINING_RUN", "manual"),
                        "commit": os.getenv("MODEL_COMMIT_SHA", "unknown"),
                    },
                )
                # Inject projected stats
                m_dto.home_corners = int(round(prediction.predicted_home_corners))
                m_dto.away_corners = int(round(prediction.predicted_away_corners))
                m_dto.home_yellow_cards = int(
                    round(prediction.predicted_home_yellow_cards)
                )
                m_dto.away_yellow_cards = int(
                    round(prediction.predicted_away_yellow_cards)
                )

                full_dto = MatchPredictionDTO(match=m_dto, prediction=p_dto)

                batch_data.append(
                    {
                        "match_id": match.id,
                        "league_id": league_id,
                        "data": full_dto.model_dump(),
                        "ttl_seconds": 86400 * 7,
                    }
                )
            except Exception as e:
                logger.error(f"Prediction failed for match {match.id}: {e}")

        return batch_data
    except Exception as e:
        logger.error(f"Prediction generation failed for league {league_id}: {e}")
        return []


async def train_for_league(
    league_id: str,
    league_matches: List[Any],
    stats_service: StatisticsService,
    learning_service: LearningService,
    args: Any,
    repo: Any,
    aggregator: Any,
    pred_service: PredictionService,
    picks_service: Any,
) -> None:
    """Encapsulate per-league training logic extracted from `main()`.

    Keeps behaviour identical but reduces `main()` complexity.
    """
    if len(league_matches) < 50:
        logger.warning(
            "⚠️ Skipping league %s: Not enough data (%d matches)",
            league_id,
            len(league_matches),
        )
        return

    logger.info(f"🏟️ Processing League: {league_id} ({len(league_matches)} matches)")

    # Calculate League Avgs (Specific to this league)
    league_avgs = stats_service.calculate_league_averages(league_matches)

    # Prepare Rolling Stats
    team_stats_cache, training_tasks = build_training_tasks(
        league_matches, stats_service, learning_service, league_avgs
    )

    if not training_tasks:
        return

    x, y_corners, y_cards, y_outcome = extract_features_from_tasks(training_tasks, args)

    # --- TRAIN MODELS ---
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score

    # 1. Corners Regressor
    logger.info(f"   📐 Training Corners Regressor ({league_id})...")
    reg_corners = RandomForestRegressor(
        n_estimators=150,
        max_depth=25,
        min_samples_leaf=2,
        n_jobs=args.n_jobs,
        random_state=42,
    )

    tscv = TimeSeriesSplit(n_splits=3)

    reg_corners.fit(x, y_corners)

    preds = reg_corners.predict(x)
    std_dev = np.std(preds)
    unique, counts = np.unique(np.round(preds), return_counts=True)
    max_dominance = np.max(counts) / len(preds) if len(preds) > 0 else 0

    logger.info(
        f"      - Distribution: StdDev={std_dev:.3f}, "
        f"MaxDominance={max_dominance:.2%}"
    )

    if max_dominance > 0.90:
        logger.error(
            f"      ❌ MODE COLLAPSE DETECTED in Corners Model for {league_id}! "
            f"(90% same value). Skipping save."
        )
    elif std_dev < 0.5:
        logger.warning(
            f"      ⚠️ Low Variance in Corners Model for {league_id} "
            "(StdDev < 0.5). Model might be too conservative, "
            "but it remains in memory."
        )
    else:
        logger.info("      ✓ Corners regressor ready in memory for %s", league_id)

    # 2. Cards Regressor
    logger.info(f"   cards Training Cards Regressor ({league_id})...")
    reg_cards = RandomForestRegressor(
        n_estimators=150,
        max_depth=25,
        min_samples_leaf=2,
        n_jobs=args.n_jobs,
        random_state=42,
    )
    reg_cards.fit(x, y_cards)

    preds_c = reg_cards.predict(x)
    max_dom_c = (
        (np.unique(np.round(preds_c), return_counts=True)[1].max() / len(preds_c))
        if len(preds_c) > 0
        else 0
    )

    if max_dom_c > 0.90:
        logger.error(
            f"      ❌ MODE COLLAPSE DETECTED in Cards Model for {league_id}! "
            f"Skipping save."
        )
    else:
        logger.info("      ✓ Cards regressor ready in memory for %s", league_id)

    # 3. Match Winner Classifier
    logger.info(f"   🏆 Training Outcome Classifier ({league_id})...")
    clf_outcome = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        class_weight="balanced",
        n_jobs=args.n_jobs,
        random_state=42,
    )
    scores_acc = cross_val_score(clf_outcome, x, y_outcome, cv=tscv, scoring="accuracy")
    logger.info(f"      - Accuracy: {np.mean(scores_acc):.2%}")

    clf_outcome.fit(x, y_outcome)
    logger.info("      ✓ Outcome classifier ready in memory for %s", league_id)

    models_bundle = {"winner": clf_outcome, "corners": reg_corners, "cards": reg_cards}

    predicted_batch = await generate_league_predictions(
        league_id,
        league_matches,
        team_stats_cache,
        league_avgs,
        aggregator,
        stats_service,
        pred_service,
        picks_service,
        models_bundle,
    )
    if predicted_batch:
        repo.bulk_save_predictions(predicted_batch)


def process_match_task(task_data):
    """
    Pure function to process a single match task.
    Args:
        task_data: tuple(
            match,
            home_stats_dict,
            away_stats_dict,
            league_avgs,
            global_avgs,
            learning_weights,
        )

    Returns:
        tuple: (features, targets_dict)
    """
    global _prediction_service
    global _picks_service
    global _statistics_service
    global _feature_extractor
    global _resolution_service

    match, raw_home, raw_away, league_avgs, global_avgs, weights = task_data

    # Lazy Init in Worker Process
    if _statistics_service is None:
        init_worker(weights)

    # 1. Convert to Domain Stats (Fast)
    home_stats = _statistics_service.convert_to_domain_stats(
        match.home_team.name, raw_home
    )
    away_stats = _statistics_service.convert_to_domain_stats(
        match.away_team.name, raw_away
    )

    # 2. Extract Features (Now includes Variance/Rolling stats)
    # We create a generic pick object since we are training general models.
    from src.domain.entities.suggested_pick import (
        ConfidenceLevel,
        MarketType,
        SuggestedPick,
    )

    dummy_pick = SuggestedPick(
        market_type=MarketType.WINNER,
        market_label="Training Generic",
        probability=0.5,
        confidence_level=ConfidenceLevel.LOW,
        reasoning="Training",
        risk_level=1,
        odds=2.0,
        expected_value=0.0,
    )

    features = _feature_extractor.extract_features(
        dummy_pick, match, home_stats, away_stats
    )

    # 3. Define Targets for Regression & Classification
    targets = {
        "home_win": 1 if match.home_goals > match.away_goals else 0,
        "away_win": 1 if match.away_goals > match.home_goals else 0,
        "draw": 1 if match.home_goals == match.away_goals else 0,
        "total_corners": (match.home_corners or 0) + (match.away_corners or 0),
        "total_cards": (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0),
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
    }

    return features, targets


async def main():
    logger.info("🚀 Starting Per-League ML Training Pipeline...")
    start_time = time.time()

    # Parse CLI args
    args = parse_args()

    from src.dependencies import (
        get_match_aggregator_service,
        get_persistence_repository,
        get_statistics_service,
        get_training_data_service,
    )

    # Determine Leagues
    leagues_to_fetch = [args.league] if args.league else DEFAULT_LEAGUES

    repo = get_persistence_repository()
    clear_stale_predictions(repo, league_ids=leagues_to_fetch)

    training_service = get_training_data_service()
    stats_service = get_statistics_service()
    learning_service = LearningService(persistence_repo=repo)

    try:
        # Fetch Data
        logger.info(
            f"📥 Fetching Training Data ({args.days} days) for {leagues_to_fetch}..."
        )
        matches = await training_service.fetch_comprehensive_training_data(
            leagues=leagues_to_fetch, days_back=args.days, force_refresh=False
        )
        logger.info(f"✅ Loaded {len(matches)} matches.")

        # Sort Chronologically and group
        matches.sort(key=lambda x: x.match_date.replace(tzinfo=None))
        matches_by_league = group_matches_by_league(matches)

        # --- SETUP PREDICTION SERVICES ---
        aggregator = get_match_aggregator_service()
        pred_service = PredictionService()
        from src.domain.services.ai_picks_service import AIPicksService

        weights = learning_service.get_learning_weights()
        picks_service = AIPicksService(learning_weights=weights, persistence_repo=repo)

        # Train per league (delegated)
        for league_id, league_matches in matches_by_league.items():
            await train_for_league(
                league_id,
                league_matches,
                stats_service,
                learning_service,
                args,
                repo,
                aggregator,
                pred_service,
                picks_service,
            )

        elapsed = time.time() - start_time
        logger.info(f"🎉 Training Completed in {elapsed:.2f} seconds.")
    finally:
        cleanup_model_artifacts(logger)


if __name__ == "__main__":
    asyncio.run(main())
