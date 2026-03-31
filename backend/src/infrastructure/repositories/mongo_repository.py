import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from pymongo import MongoClient
from src.utils.time_utils import get_current_time

logger = logging.getLogger(__name__)


class MongoRepository:
    """Drop-in replacement for PostgreSQL PersistenceRepository using MongoDB."""

    def __init__(self):
        mongo_uri = os.getenv(
            "MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/"
        )
        db_name = os.getenv("MONGO_DB_NAME", "bjj_betsports")

        try:
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            self.db = self.client[db_name]

            # Initialize collections
            self.training_results = self.db["training_results"]
            self.match_predictions = self.db["match_predictions"]
            self.api_cache = self.db["api_cache"]

            # Create indexes
            self.training_results.create_index("key", unique=True)
            self.match_predictions.create_index("match_id", unique=True)
            self.api_cache.create_index("key", unique=True)

            logger.info(f"✅ Successfully connected to MongoDB database: {db_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise e

    def create_tables(self):
        """No-op for MongoDB, collections are created implicitly."""
        pass

    def save_training_result(self, key: str, data: dict):
        self.training_results.update_one(
            {"key": key},
            {"$set": {"data": data, "last_updated": get_current_time()}},
            upsert=True,
        )

    def get_training_result(self, key: str) -> Optional[dict]:
        doc = self.training_results.find_one({"key": key})
        return doc.get("data") if doc else None

    def get_training_result_with_timestamp(
        self, key: str
    ) -> Tuple[Optional[dict], Optional[datetime]]:
        doc = self.training_results.find_one({"key": key})
        if doc:
            return doc.get("data"), doc.get("last_updated")
        return None, None

    def get_training_results_by_pattern(self, pattern: str) -> dict:
        """Approximation of SQL LIKE pattern matching for MongoDB"""
        regex_pattern = pattern.replace("%", ".*")
        docs = self.training_results.find({"key": {"$regex": f"^{regex_pattern}$"}})
        return {doc["key"]: doc["data"] for doc in docs}

    def save_match_prediction(
        self, match_id: str, league_id: str, data: dict, ttl_seconds: int = 86400
    ):
        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        self.match_predictions.update_one(
            {"match_id": match_id},
            {
                "$set": {
                    "league_id": league_id,
                    "data": data,
                    "expires_at": expires_at,
                    "last_updated": get_current_time(),
                }
            },
            upsert=True,
        )

    def get_match_prediction(self, match_id: str) -> Optional[dict]:
        doc = self.match_predictions.find_one({"match_id": match_id})
        if doc and doc.get("expires_at") and doc["expires_at"] > get_current_time():
            return doc.get("data")
        return None

    def bulk_save_predictions(self, predictions_data: List[dict]):
        if not predictions_data:
            return
        from pymongo import UpdateOne

        operations = []
        for p in predictions_data:
            expires_at = get_current_time() + timedelta(
                seconds=p.get("ttl_seconds", 86400)
            )
            operations.append(
                UpdateOne(
                    {"match_id": p["match_id"]},
                    {
                        "$set": {
                            "league_id": p["league_id"],
                            "data": p["data"],
                            "expires_at": expires_at,
                            "last_updated": get_current_time(),
                        }
                    },
                    upsert=True,
                )
            )
        self.match_predictions.bulk_write(operations)

    def get_all_active_predictions(self) -> List[dict]:
        docs = self.match_predictions.find({"expires_at": {"$gt": get_current_time()}})
        return [
            {
                "match_id": doc["match_id"],
                "prediction": doc["data"],
                "last_updated": doc.get("last_updated"),
            }
            for doc in docs
        ]

    def save_cached_response(
        self, endpoint: str, data: dict, params: dict = None, ttl_seconds: int = 3600
    ):
        key = f"{endpoint}:{str(params)}"
        expires_at = get_current_time() + timedelta(seconds=ttl_seconds)
        self.api_cache.update_one(
            {"key": key},
            {"$set": {"data": data, "expires_at": expires_at}},
            upsert=True,
        )

    def get_cached_response(self, endpoint: str, params: dict = None) -> Optional[dict]:
        key = f"{endpoint}:{str(params)}"
        doc = self.api_cache.find_one({"key": key})
        # Check expiration - assuming get_current_time and expires_at are compatible
        if doc and doc.get("expires_at") and doc["expires_at"] > get_current_time():
            return doc.get("data")
        return None

    def clear_all_predictions(self):
        self.match_predictions.delete_many({})

    def clear_all_data(self) -> Dict[str, int]:
        """Clear training, predictions and API cache collections."""
        training_deleted = self.training_results.delete_many({}).deleted_count
        predictions_deleted = self.match_predictions.delete_many({}).deleted_count
        cache_deleted = self.api_cache.delete_many({}).deleted_count

        return {
            "training_results": training_deleted,
            "match_predictions": predictions_deleted,
            "api_cache": cache_deleted,
        }


# Singleton accessor with old name alias to avoid changing dependencies everywhere
_mongo_repo = None


def get_mongo_repository() -> MongoRepository:
    global _mongo_repo
    if _mongo_repo is None:
        _mongo_repo = MongoRepository()
    return _mongo_repo
