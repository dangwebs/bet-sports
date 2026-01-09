import logging
import json
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import Column, String, JSON, DateTime, Integer
from src.infrastructure.database.database_service import Base, DatabaseService, get_database_service

logger = logging.getLogger(__name__)

class TrainingResultModel(Base):
    """
    SQLAlchemy model for storing training results.
    """
    __tablename__ = "training_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, index=True, nullable=False) # e.g., "latest_daily"
    data = Column(JSON, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MatchPredictionModel(Base):
    """
    SQLAlchemy model for storing pre-calculated match predictions.
    """
    __tablename__ = "match_predictions"
    
    match_id = Column(String, primary_key=True, index=True)
    league_id = Column(String, index=True)
    data = Column(JSON, nullable=False) # Prediction details and picks
    expires_at = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApiCacheModel(Base):
    """
    SQLAlchemy model for caching API responses.
    """
    __tablename__ = "api_response_cache"
    
    endpoint = Column(String, primary_key=True)  # Full endpoint path e.g. /competitions/PL/matches
    params = Column(String, primary_key=True, default="") # Flattened params string
    response_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class PersistenceRepository:
    """
    Repository for persisting complex data structures to the database.
    Includes robust retry mechanisms and type enforcement.
    """
    
    def __init__(self, db_service: DatabaseService = None):
        self.db_service = db_service or get_database_service()

    def create_tables(self):
        """Create all tables defined in Base."""
        self.db_service.create_tables()

    def _sanitize_json_data(self, data: Any) -> Any:
        """
        Sanitize data for JSON storage, handling datetime and Numpy objects recursively.
        """
        import numpy as np
        import pandas as pd

        class RobustJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, datetime):
                    return o.isoformat()
                if isinstance(o, (np.int_, np.intc, np.intp, np.int8,
                                  np.int16, np.int32, np.int64, np.longlong)):
                    return int(o)
                if isinstance(o, (np.float_, np.float16, np.float32, np.float64)):
                    return float(o)
                if isinstance(o, (np.bool_)):
                    return bool(o)
                if isinstance(o, np.ndarray):
                    return o.tolist()
                if isinstance(o, pd.Timestamp):
                    return o.isoformat()
                if pd.isna(o): # Handle NaN/None in pandas
                    return None
                return super().default(o)
                
        # Dump to string and reload to ensure pure JSON types
        return json.loads(json.dumps(data, cls=RobustJSONEncoder))

    def _execute_with_retry(self, operation: callable, retries: int = 3, delay: int = 1):
        """
        Execute a database operation with robust retries and exponential backoff.
        """
        import time
        from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError
        
        last_error = None
        for attempt in range(retries):
            session = self.db_service.get_session()
            try:
                result = operation(session)
                session.commit()
                return result
            except (OperationalError, DisconnectionError, TimeoutError) as e:
                session.rollback()
                last_error = e
                logger.warning(f"Database operation failed (Attempt {attempt+1}/{retries}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            except Exception as e:
                session.rollback()
                logger.error(f"Unrecoverable database error: {e}")
                raise e
            finally:
                session.close()
        
        logger.error(f"Database operation failed after {retries} attempts.")
        raise last_error

    def save_training_result(self, key: str, data: dict) -> bool:
        """
        Save or update a training result by key with retries.
        """
        try:
            # 1. Sanitize Data first (CPU bound, no DB needed)
            sanitized_data = self._sanitize_json_data(data)
            
            def _op(session):
                record = session.query(TrainingResultModel).filter(TrainingResultModel.key == key).first()
                if record:
                    record.data = sanitized_data
                    record.last_updated = datetime.utcnow()
                else:
                    record = TrainingResultModel(key=key, data=sanitized_data)
                    session.add(record)
                return True

            return self._execute_with_retry(_op, retries=5, delay=2)
            
        except Exception as e:
            logger.error(f"Failed to save training result '{key}': {e}")
            return False

    def get_training_result(self, key: str) -> dict:
        """Retrieve a training result by key."""
        result, _ = self.get_training_result_with_timestamp(key)
        return result

    def get_training_result_with_timestamp(self, key: str) -> tuple[Optional[dict], Optional[datetime]]:
        """Retrieve a training result and its last_updated timestamp."""
        session = self.db_service.get_session()
        try:
            record = session.query(TrainingResultModel).filter(TrainingResultModel.key == key).first()
            if record:
                return record.data, record.last_updated
            return None, None
        except Exception as e:
            logger.error(f"Failed to retrieve training result with timestamp: {e}")
            return None, None
        finally:
            session.close()

    def get_last_updated(self, key: str) -> datetime:
        """Get the last updated timestamp for a result."""
        session = self.db_service.get_session()
        try:
            record = session.query(TrainingResultModel).filter(TrainingResultModel.key == key).first()
            if record:
                return record.last_updated
            return None
        except Exception as e:
            logger.error(f"Failed to get last updated timestamp: {e}")
            return None
        finally:
            session.close()

    def get_training_results_by_pattern(self, pattern: str) -> dict[str, dict]:
        """
        Retrieve all training results where the key matches the SQL pattern (e.g. 'top_ml_%').
        Returns a dict mapping key -> data.
        """
        session = self.db_service.get_session()
        try:
            records = session.query(TrainingResultModel).filter(
                TrainingResultModel.key.like(pattern)
            ).all()
            return {r.key: r.data for r in records}
        except Exception as e:
            logger.error(f"Failed to retrieve training results by pattern '{pattern}': {e}")
            return {}
        finally:
            session.close()

    def save_match_prediction(self, match_id: str, league_id: str, data: dict, ttl_seconds: int = 86400) -> bool:
        """Save or update a match prediction with an expiration time."""
        try:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            sanitized_data = self._sanitize_json_data(data)

            def _op(session):
                record = session.query(MatchPredictionModel).filter(MatchPredictionModel.match_id == match_id).first()
                if record:
                    record.league_id = league_id
                    record.data = sanitized_data
                    record.expires_at = expires_at
                    record.last_updated = datetime.utcnow()
                else:
                    record = MatchPredictionModel(
                        match_id=match_id,
                        league_id=league_id,
                        data=sanitized_data,
                        expires_at=expires_at
                    )
                    session.add(record)
                return True

            return self._execute_with_retry(_op)
        except Exception as e:
            logger.error(f"Failed to save match prediction {match_id}: {e}")
            return False

    def get_match_prediction(self, match_id: str) -> Optional[dict]:
        """Retrieve a valid prediction by match ID."""
        data, _ = self.get_match_prediction_with_timestamp(match_id)
        return data

    def get_match_prediction_with_timestamp(self, match_id: str) -> tuple[Optional[dict], Optional[datetime]]:
        """Retrieve a valid prediction and its last_updated timestamp."""
        session = self.db_service.get_session()
        try:
            now = datetime.utcnow()
            record = session.query(MatchPredictionModel).filter(
                MatchPredictionModel.match_id == match_id,
                MatchPredictionModel.expires_at > now
            ).first()
            if record:
                return record.data, record.last_updated
            return None, None
        except Exception as e:
            logger.error(f"Failed to retrieve match prediction with timestamp {match_id}: {e}")
            return None, None
        finally:
            session.close()

    def get_league_predictions(self, league_id: str) -> list[dict]:
        """Retrieve all valid predictions for a specific league."""
        session = self.db_service.get_session()
        try:
            now = datetime.utcnow()
            records = session.query(MatchPredictionModel).filter(
                MatchPredictionModel.league_id == league_id,
                MatchPredictionModel.expires_at > now
            ).all()
            return [r.data for r in records]
        except Exception as e:
            logger.error(f"Failed to retrieve league predictions {league_id}: {e}")
            return []
        finally:
            session.close()

    def get_all_active_predictions(self) -> list[dict]:
        """Retrieve all valid predictions across all leagues."""
        session = self.db_service.get_session()
        try:
            now = datetime.utcnow()
            records = session.query(MatchPredictionModel).filter(
                MatchPredictionModel.expires_at > now
            ).all()
            return [r.data for r in records]
        except Exception as e:
            logger.error(f"Failed to retrieve all active predictions: {e}")
            return []
        finally:
            session.close()

    def clear_all_predictions(self) -> bool:
        """
        Clear all stored match predictions.
        Useful when retraining models to ensure fresh predictions are generated.
        """
        session = self.db_service.get_session()
        try:
            # Delete all rows in the match_predictions table
            deleted_count = session.query(MatchPredictionModel).delete()
            session.commit()
            logger.info(f"🗑️ Cleared {deleted_count} match predictions from database.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear predictions: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def clear_all_training_results(self) -> bool:
        """
        Clear all stored training results.
        Useful for a complete reset of ML pipeline data.
        """
        session = self.db_service.get_session()
        try:
            deleted_count = session.query(TrainingResultModel).delete()
            session.commit()
            logger.info(f"🗑️ Cleared {deleted_count} training results from database.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear training results: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def clear_all_api_cache(self) -> bool:
        """
        Clear all cached API responses.
        Forces fresh data fetches from external APIs.
        """
        session = self.db_service.get_session()
        try:
            deleted_count = session.query(ApiCacheModel).delete()
            session.commit()
            logger.info(f"🗑️ Cleared {deleted_count} cached API responses from database.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear API cache: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def clear_all_data(self) -> dict:
        """
        Clear ALL data from all tables (predictions, training results, API cache).
        Use with caution - this is a complete database reset for ML data.
        Returns a summary of what was cleared.
        """
        results = {
            "predictions_cleared": self.clear_all_predictions(),
            "training_results_cleared": self.clear_all_training_results(),
            "api_cache_cleared": self.clear_all_api_cache()
        }
        all_success = all(results.values())
        if all_success:
            logger.info("✅ Successfully cleared ALL ML data from database.")
        else:
            logger.warning(f"⚠️ Partial clear - some operations failed: {results}")
        return results

    def bulk_save_predictions(self, predictions_batch: list[dict], chunk_size: int = 50) -> bool:
        """
        Save multiple predictions in chunks with retry.
        Each dict in 'predictions_batch' should have: match_id, league_id, data, and optionally ttl_seconds.
        """
        from datetime import timedelta
        
        if not predictions_batch:
            return True
            
        success = True
        total_chunks = (len(predictions_batch) + chunk_size - 1) // chunk_size
        
        logger.info(f"Bulk saving {len(predictions_batch)} predictions in {total_chunks} chunks...")

        for i in range(0, len(predictions_batch), chunk_size):
            chunk = predictions_batch[i:i + chunk_size]
            try:
                # Pre-sanitize chunk
                now = datetime.utcnow()
                sanitized_chunk = []
                for p in chunk:
                    ttl = p.get('ttl_seconds', 86400 * 7)
                    expires = now + timedelta(seconds=ttl)
                    
                    sanitized_chunk.append({
                        "match_id": p['match_id'],
                        "league_id": p['league_id'],
                        "data": self._sanitize_json_data(p['data']),
                        "expires_at": expires,
                        "last_updated": now
                    })
                
                def _op(session):
                    # Upsert Logic manually for batch
                    for item in sanitized_chunk:
                        match_id = item['match_id']
                        # Try to notify existing
                        record = session.query(MatchPredictionModel).filter(MatchPredictionModel.match_id == match_id).first()
                        if record:
                            record.league_id = item['league_id']
                            record.data = item['data']
                            record.expires_at = item['expires_at']
                            record.last_updated = item['last_updated']
                        else:
                            record = MatchPredictionModel(
                                match_id=match_id,
                                league_id=item['league_id'],
                                data=item['data'],
                                expires_at=item['expires_at'],
                                last_updated=item['last_updated']
                            )
                            session.add(record)
                    return True
                
                self._execute_with_retry(_op, retries=3, delay=1)
                
            except Exception as e:
                logger.error(f"Failed to save chunk {i//chunk_size}: {e}")
                success = False # Continue trying other chunks, but mark partial failure
        
        return success

    # =============================================================================
    # API Response Caching (for Football-Data.org, etc.)
    # =============================================================================
    
    def get_cached_response(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """
        Retrieve a cached API response if it exists and hasn't expired.
        """
        params_key = json.dumps(params or {}, sort_keys=True)
        session = self.db_service.get_session()
        try:
            record = session.query(ApiCacheModel).filter(
                ApiCacheModel.endpoint == endpoint,
                ApiCacheModel.params == params_key,
                ApiCacheModel.expires_at > datetime.utcnow()
            ).first()
            if record:
                return record.response_json
            return None
        except Exception as e:
            logger.warning(f"Failed to read API cache: {e}")
            return None
        finally:
            session.close()

    def save_cached_response(self, endpoint: str, data: dict, params: dict = None, ttl_seconds: int = 3600) -> bool:
        """
        Save an API response to the cache with an expiration time.
        """
        from datetime import timedelta
        
        params_key = json.dumps(params or {}, sort_keys=True)
        sanitized_data = self._sanitize_json_data(data)
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        def _op(session):
            # Try to find existing record
            record = session.query(ApiCacheModel).filter(
                ApiCacheModel.endpoint == endpoint,
                ApiCacheModel.params == params_key
            ).first()
            
            if record:
                record.response_json = sanitized_data
                record.expires_at = expires_at
                record.created_at = datetime.utcnow()
            else:
                record = ApiCacheModel(
                    endpoint=endpoint,
                    params=params_key,
                    response_json=sanitized_data,
                    expires_at=expires_at
                )
                session.add(record)
            return True
        
        try:
            self._execute_with_retry(_op, retries=2, delay=1)
            return True
        except Exception as e:
            logger.error(f"Failed to save API cache: {e}")
            return False

def get_persistence_repository() -> PersistenceRepository:
    """Get the persistence repository instance."""
    return PersistenceRepository()
