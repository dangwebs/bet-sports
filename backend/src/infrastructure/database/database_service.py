import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseService:
    """
    Service for managing database connections and sessions.
    """
    
    def __init__(self, db_url: str = None):
        # Priority: db_url param -> DATABASE_URL env
        self.db_url = db_url or os.getenv("DATABASE_URL")
        
        if not self.db_url:
            # Fail Fast: The application must not run without a configured PostgreSQL database.
            raise ValueError("DATABASE_URL environment variable is not set. Cannot initialize database.")
        
        # Adjust URL for SQLAlchemy if it starts with postgres:// (old Heroku/Render format)
        if self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)
        
        if "sqlite" in self.db_url:
            raise ValueError("SQLite is not supported. The application must use a PostgreSQL database.")

        self._initialize_engine()

    def _initialize_engine(self):
        try:
            # Create engine
            # pool_pre_ping=True helps with dropped connections (common in cloud envs)
            self.engine = create_engine(
                self.db_url,
                pool_pre_ping=True
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Verify connection immediately
            with self.engine.connect():
                db_type = "PostgreSQL"
                host_info = self.db_url.split('@')[-1] if '@' in self.db_url else "local file"
                logger.info(f"✅ Database connection successful ({db_type}): {host_info}")
            
        except Exception as e:
            logger.error(f"FATAL: Failed to initialize DatabaseService with PostgreSQL: {self.db_url}: {e}")
            raise e # Re-raise the exception to stop the application startup

    def create_tables(self):
        """Create all tables defined in Base."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise e

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

# Singleton instance access
_db_instance = None

def get_database_service() -> DatabaseService:
    """Get the singleton database service instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
    return _db_instance
