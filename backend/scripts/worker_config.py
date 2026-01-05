"""
Worker Configuration
Configuration settings for the prediction worker script.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app_persistence.db")

# API Keys
FOOTBALL_DATA_ORG_KEY = os.getenv("FOOTBALL_DATA_ORG_KEY")
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Worker Configuration
WORKER_MODE = True  # Always True for worker script
DAYS_BACK = int(os.getenv("DAYS_BACK", 550))  # Historical data window (1.5 years)
PREDICTION_LIMIT = int(os.getenv("PREDICTION_LIMIT", 50))  # Max predictions per league

# Leagues to process (from constants)
from src.core.constants import DEFAULT_LEAGUES
env_leagues = os.getenv("LEAGUES_TO_PROCESS")
if env_leagues:
    LEAGUES_TO_PROCESS = [l.strip() for l in env_leagues.split(",")]
else:
    LEAGUES_TO_PROCESS = DEFAULT_LEAGUES

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Performance Settings
BATCH_SIZE = 100  # Batch size for database inserts
MAX_WORKERS = 4  # Parallel processing workers
MEMORY_LIMIT_MB = 2048  # Memory limit for worker (GitHub Actions has more RAM)

# Cache Settings (for worker)
ENABLE_WORKER_CACHE = True
CACHE_TTL_SECONDS = 3600  # 1 hour cache for intermediate results
