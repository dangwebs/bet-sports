"""
Auto-labeler service

Scans persisted match predictions and, when match results are available,
writes label information back to the persistence repository so downstream
components (training, metrics) can use labeled data.
"""
import logging
import os

from src.utils.time_utils import get_current_time
from src.application.services.auto_labeler_rules import derive_market_labels

logger = logging.getLogger(__name__)


class AutoLabeler:
    """Simple auto-labeler that marks expired predictions as labeled when
    finished match results are available from data sources or cache.

    This is intentionally conservative: it only labels when a finished result
    can be confidently retrieved.
    """

    def __init__(self, persistence_repo, data_sources, cache_service=None):
        self.persistence_repo = persistence_repo
        self.data_sources = data_sources
        self.cache_service = cache_service

    async def run(self, limit: int = 1000) -> int:
        """Run the labeling pass.

        Returns the number of documents labeled.
        """
        labeled = 0
        now = get_current_time()

        try:
            # Query for expired predictions that are not yet labeled
            cursor = self.persistence_repo.match_predictions.find(
                {"expires_at": {"$lte": now}, "labeled": {"$ne": True}}
            )

            async_count = 0
            for doc in cursor:
                if labeled >= limit:
                    break
                match_id = doc.get("match_id")
                try:
                    match = None
                    # 1) Try Football-Data.org if configured
                    if hasattr(self.data_sources, "football_data_org") and getattr(
                        self.data_sources.football_data_org, "is_configured", False
                    ):
                        try:
                            match = await self.data_sources.football_data_org.get_match_details(
                                match_id
                            )
                            label_source = "football_data_org"
                        except Exception:
                            match = None

                    # 2) Fallback to cached match forecast if available
                    if not match and self.cache_service:
                        try:
                            key = f"forecasts:match_{match_id}"
                            cached = self.cache_service.get(key)
                            if cached and cached.get("match"):
                                match = cached["match"]
                                label_source = "cache"
                        except Exception:
                            match = None

                    if not match:
                        continue

                    status = getattr(match, "status", "").upper()
                    if status not in ("FINISHED", "FT", "ENDED"):
                        # Not finished yet
                        continue

                    # Attempt to extract final score
                    home_goals = getattr(match, "home_goals", None) or getattr(
                        match, "home_score", None
                    )
                    away_goals = getattr(match, "away_goals", None) or getattr(
                        match, "away_score", None
                    )

                    label_payload = {
                        "labeled": True,
                        "label": {
                            "home_goals": home_goals,
                            "away_goals": away_goals,
                            "home_corners": getattr(match, "home_corners", None),
                            "away_corners": getattr(match, "away_corners", None),
                            "home_yellow_cards": getattr(
                                match, "home_yellow_cards", None
                            ),
                            "away_yellow_cards": getattr(
                                match, "away_yellow_cards", None
                            ),
                        },
                        "label_source": label_source,
                        "label_metadata": {
                            "labeled_by": "auto_labeler",
                            "model_version": os.getenv("MODEL_VERSION", "unknown"),
                        },
                        "labeled_at": get_current_time(),
                    }

                    # Derive per-market labels (winner, over/under, ...)
                    try:
                        market_labels = derive_market_labels(doc, match)
                        if market_labels:
                            label_payload["label"]["market_labels"] = market_labels
                    except Exception:
                        # Keep labeling robust: failure to derive market labels
                        # should not block the main labeling path.
                        logger.exception("Failed deriving market labels for %s", match_id)

                    # Persist label to the match_predictions doc
                    self.persistence_repo.match_predictions.update_one(
                        {"match_id": match_id}, {"$set": label_payload}
                    )
                    labeled += 1

                except Exception as e:
                    logger.warning("AutoLabeler failed for %s: %s", match_id, e)
                    continue

        except Exception as exc:
            logger.error("AutoLabeler encountered an error: %s", exc, exc_info=True)

        logger.info("AutoLabeler labeled %d documents", labeled)
        return labeled
