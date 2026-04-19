"""
Learning Service Module

Domain service for continuous learning based on betting feedback.
Persists learning weights to JSON file for cross-restart learning.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from pytz import timezone
from src.domain.entities.betting_feedback import (
    BettingFeedback,
    LearningWeights,
    MarketPerformance,
)

logger = logging.getLogger(__name__)


class LearningService:
    """
    Service for managing continuous learning from betting feedback.

    Responsibilities:
    - Load/save learning weights to persistent storage
    - Process betting feedback and update weights
    - Provide market-specific confidence adjustments
    """

    DEFAULT_WEIGHTS_PATH = "learning_weights.json"
    MONGO_KEY = "learning_weights"

    def __init__(
        self,
        weights_path: Optional[str] = None,
        persistence_repo: Optional[Any] = None,
    ):
        """
        Initialize learning service.

        Args:
            weights_path: Path to JSON file for persisting weights (fallback/migration)
            persistence_repo: Repository for DB persistence
        """
        self.weights_path = weights_path or self.DEFAULT_WEIGHTS_PATH
        self.repo = persistence_repo
        self._learning_weights: Optional[LearningWeights] = None

    @property
    def learning_weights(self) -> LearningWeights:
        """Lazily load and return the learning weights."""
        if self._learning_weights is None:
            self._learning_weights = self._load_weights()
        return self._learning_weights

    def _load_weights(self) -> LearningWeights:
        """Load learning weights from DB or JSON file (migration)."""
        # 1. Try DB first
        if self.repo:
            data = self.repo.get_app_state(self.MONGO_KEY)
            if data:
                return self._reconstruct_weights(data)

        # 2. Migration: Try local file if DB empty
        if not os.path.exists(self.weights_path):
            logger.info("No weights found in DB or local file, starting fresh")
            return LearningWeights()

        try:
            logger.info(f"🔄 Migrating weights from {self.weights_path} to Database...")
            with open(self.weights_path, "r") as f:
                data = json.load(f)

            weights = self._reconstruct_weights(data)

            # Save to DB immediately if repo available
            if self.repo:
                self._save_to_db(weights)
                # Cleanup local file after successful migration
                try:
                    os.remove(self.weights_path)
                    logger.info(f"🗑️ Removed migrated file: {self.weights_path}")
                except Exception as del_err:
                    logger.warning(f"Failed to remove migrated file: {del_err}")

            return weights
        except Exception as e:
            logger.error(f"Failed to load/migrate weights: {e}, starting fresh")
            return LearningWeights()

    def _reconstruct_weights(self, data: dict) -> LearningWeights:
        """Helper to reconstruct LearningWeights from dict."""
        # Reconstruct MarketPerformance objects
        market_perfs = {}
        for market_type, perf_data in data.get("market_performances", {}).items():
            # Handle datetime field
            if "last_updated" in perf_data and isinstance(perf_data["last_updated"], str):
                perf_data["last_updated"] = datetime.fromisoformat(
                    perf_data["last_updated"]
                )
            market_perfs[market_type] = MarketPerformance(**perf_data)

        # Handle datetime field for LearningWeights
        last_saved = data.get("last_saved")
        if last_saved and isinstance(last_saved, str):
            last_saved = datetime.fromisoformat(last_saved)
        else:
            last_saved = datetime.now(timezone("America/Bogota"))

        return LearningWeights(
            market_performances=market_perfs,
            global_adjustments=data.get("global_adjustments", {}),
            version=data.get("version", "1.0"),
            last_saved=last_saved,
        )

    def _save_weights(self) -> None:
        """Save learning weights to DB (primary) and JSON file (legacy/transitional)."""
        if self.repo:
            self._save_to_db(self.learning_weights)

        # Still attempt file save if not yet deleted?
        # The user specifically asked to ELIMINATE heavy/unnecessary files.
        # Once migrated, we stop writing to disk.
        if not os.path.exists(self.weights_path):
            return

        try:
            # Legacy file save (only if file still exists - fallback)
            data = self._serialize_weights(self.learning_weights)
            with open(self.weights_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save weights to file: {e}")

    def _save_to_db(self, weights: LearningWeights) -> None:
        """Save weights to MongoDB."""
        try:
            data = self._serialize_weights(weights)
            self.repo.save_app_state(self.MONGO_KEY, data)
            logger.debug("Saved learning weights to Database")
        except Exception as e:
            logger.error(f"Failed to save weights to DB: {e}")

    def _serialize_weights(self, weights: LearningWeights) -> dict:
        """Helper to serialize LearningWeights to dict."""
        data = {
            "market_performances": {},
            "global_adjustments": weights.global_adjustments,
            "version": weights.version,
            "last_saved": datetime.now(timezone("America/Bogota")).isoformat(),
        }

        for market_type, perf in weights.market_performances.items():
            perf_dict = {
                "market_type": perf.market_type,
                "total_predictions": perf.total_predictions,
                "correct_predictions": perf.correct_predictions,
                "success_rate": perf.success_rate,
                "avg_odds": perf.avg_odds,
                "total_profit_loss": perf.total_profit_loss,
                "confidence_adjustment": perf.confidence_adjustment,
                "last_updated": perf.last_updated.isoformat(),
            }
            data["market_performances"][market_type] = perf_dict
        return data

    def register_feedback(self, feedback: BettingFeedback) -> None:
        """
        Register betting feedback and update learning weights.

        Args:
            feedback: Betting outcome feedback
        """
        self.learning_weights.update_with_feedback(feedback)
        self._save_weights()

        logger.info(
            f"Registered feedback for market {feedback.market_type}: "
            f"{'correct' if feedback.was_correct else 'incorrect'}"
        )

    def get_market_adjustment(self, market_type: str) -> float:
        """
        Get confidence adjustment for a market type.

        Args:
            market_type: Type of market

        Returns:
            Adjustment multiplier (0.5 - 1.3)
        """
        return self.learning_weights.get_market_adjustment(market_type)

    def get_market_stats(self, market_type: str) -> Optional[MarketPerformance]:
        """
        Get performance statistics for a market type.

        Args:
            market_type: Type of market

        Returns:
            MarketPerformance or None if no data
        """
        return self.learning_weights.market_performances.get(market_type)

    def get_all_stats(self) -> dict[str, MarketPerformance]:
        """Get all market performance statistics."""
        return self.learning_weights.market_performances

    def get_learning_weights(self) -> LearningWeights:
        """Get the current learning weights object."""
        return self.learning_weights

    def reset_weights(self) -> None:
        """Reset all learning weights to default."""
        self._learning_weights = LearningWeights()
        self._save_weights()
        logger.info("Reset all learning weights to default")
