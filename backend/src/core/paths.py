
import os
from pathlib import Path

# /backend/src/core/paths.py
# __file__ = backend/src/core/paths.py
# .parent = backend/src/core
# .parent.parent = backend/src
# .parent.parent.parent = backend

BACKEND_SRC_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = BACKEND_SRC_ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent

DATA_DIR = BACKEND_ROOT / "data"
MODEL_FILE_PATH = DATA_DIR / "ml_picks_classifier.joblib"

# Ensure data dir exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
