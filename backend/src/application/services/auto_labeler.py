"""
Auto-labeler service

Scans persisted match predictions and, when match results are available,
writes label information back to the persistence repository so downstream
components (training, metrics) can use labeled data.
"""
import logging
import os

from src.application.services.auto_labeler_rules import derive_market_labels
from src.utils.time_utils import get_current_time

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

            for doc in cursor:
                if labeled >= limit:
                    break
                match_id = doc.get("match_id")
                try:
                    match, source = await self._fetch_match(match_id)
                    if not match:
                        continue

                    if not self._is_finished(match):
                        continue

                    payload = self._build_label_payload(doc, match, source)

                    # Persist label to the match_predictions doc
                    self.persistence_repo.match_predictions.update_one(
                        {"match_id": match_id}, {"$set": payload}
                    )
                    labeled += 1

                except Exception as e:
                    logger.warning("AutoLabeler failed for %s: %s", match_id, e)
                    continue

        except Exception as exc:
            logger.error("AutoLabeler encountered an error: %s", exc, exc_info=True)

        logger.info("AutoLabeler labeled %d documents", labeled)
        return labeled

    async def _fetch_match(self, match_id):
        """Attempt to fetch match details from configured datasources or cache.

        Returns a tuple (match, source) where source is a string describing
        where the match came from (e.g. 'football_data_org' or 'cache').
        """
        match = None
        source = None

        # 1) Try Football-Data.org if configured
        if hasattr(self.data_sources, "football_data_org") and getattr(
            self.data_sources.football_data_org, "is_configured", False
        ):
            try:
                match = await self.data_sources.football_data_org.get_match_details(
                    match_id
                )
                source = "football_data_org"
            except Exception:
                match = None

        # 2) Fallback to cached match forecast if available
        if not match and self.cache_service:
            try:
                key = f"forecasts:match_{match_id}"
                cached = self.cache_service.get(key)
                if cached and cached.get("match"):
                    match = cached["match"]
                    source = "cache"
            except Exception:
                match = None

        return match, source

    def _is_finished(self, match) -> bool:
        status = getattr(match, "status", "").upper()
        return status in ("FINISHED", "FT", "ENDED")

    def _extract_scores(self, match):
        home_goals = getattr(match, "home_goals", None) or getattr(
            match, "home_score", None
        )
        away_goals = getattr(match, "away_goals", None) or getattr(
            match, "away_score", None
        )
        return home_goals, away_goals

    def _build_label_payload(self, doc, match, label_source: str):
        home_goals, away_goals = self._extract_scores(match)

        label_payload = {
            "labeled": True,
            "label": {
                "home_goals": home_goals,
                "away_goals": away_goals,
                "home_corners": getattr(match, "home_corners", None),
                "away_corners": getattr(match, "away_corners", None),
                "home_yellow_cards": getattr(match, "home_yellow_cards", None),
                "away_yellow_cards": getattr(match, "away_yellow_cards", None),
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
            logger.exception(
                "Failed deriving market labels for %s", doc.get("match_id")
            )

        return label_payload
