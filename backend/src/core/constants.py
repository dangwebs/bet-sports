"""
Centralized constants for the BJJ-BetSports backend.
"""

# Default leagues used for training and predictions (§15.B compliant)
DEFAULT_LEAGUES = ["E0", "SP1", "D1", "I1", "F1", "P1"]

# ML Model Configuration
ML_MODEL_FILENAME = "ml_picks_classifier.joblib"

# Probability Thresholds (§3 No Hardcoding)
PROBABILITY_THRESHOLDS = {
    "high": 0.65,
    "medium": 0.50,
    "low": 0.35,
    "draw_adjusted": 0.35,
    "volatile_base": 0.50,
    "standard_base": 0.45,
}

# ML Confidence Thresholds
ML_CONFIDENCE_THRESHOLDS = {
    "top_pick": 0.80,
    "favorable": 0.65,
    "skeptical": 0.50,
}

# Recommendation Threshold
RECOMMENDATION_THRESHOLD = 0.65

# Color Codes for Frontend (Fuente Única de Verdad)
COLOR_CODES = {
    "high": "#10b981",    # Green (≥65%)
    "medium": "#f59e0b",  # Amber (35-64%)
    "low": "#ef4444",     # Red (<35%)
}
