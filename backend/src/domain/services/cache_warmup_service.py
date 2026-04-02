from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List, Optional

from src.application.use_cases.use_cases import DataSources, GetPredictionsUseCase
from src.domain.services.match_aggregator_service import MatchAggregatorService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService

# from src.domain.services.risk_management.risk_manager import RiskManager

if TYPE_CHECKING:
    from src.infrastructure.repositories.mongo_repository import MongoRepository
    from src.infrastructure.services.background_processor import BackgroundProcessor

logger = logging.getLogger(__name__)


class CacheWarmupService:
    """
    Service responsible for warming up the cache.
    Uses GetPredictionsUseCase to ensure consistency with the API.
    """

    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        match_aggregator: MatchAggregatorService,
        persistence_repository: Optional[MongoRepository] = None,
        background_processor: Optional[BackgroundProcessor] = None,
    ) -> None:
        self.use_case = GetPredictionsUseCase(
            data_sources=data_sources,
            prediction_service=prediction_service,
            statistics_service=statistics_service,
            match_aggregator=match_aggregator,
            # risk_manager=risk_manager,
            persistence_repository=persistence_repository,
            background_processor=background_processor,
        )

    async def warm_up_predictions(self, league_ids: Optional[List[str]] = None) -> None:
        """
        Warms up predictions for specific leagues or all priority leagues.
        """
        if not league_ids:
            # Default priority leagues (§15.B compliant - 6 top-tier only)
            league_ids = ["E0", "SP1", "D1", "I1", "F1", "P1"]

        logger.info(
            "🔥 Starting Unified Cache Warmup for %s leagues...",
            len(league_ids),
        )

        # We process sequentially to avoid CPU/RAM spikes on low-resource servers
        for league_id in league_ids:
            try:
                logger.info("🔥 Warming up league: %s", league_id)
                # Execute handles Cache -> Persistence -> Real-time logic
                await self.use_case.execute(league_id, limit=30)
                # Small sleep to yield to other tasks
                await asyncio.sleep(1)
            except Exception as e:
                logger.error("Failed to warm up league %s: %s", league_id, e)

        logger.info("🔥 Cache Warmup Complete.")
