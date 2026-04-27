"""
Domain exceptions for the prediction system.
"""


class PredictionError(Exception):
    """Base exception for prediction-related errors."""

    pass


PredictionException = PredictionError


class InsufficientDataError(PredictionError):
    """Exception raised when there is not enough historical data to
    generate a reliable prediction.
    """

    pass


InsufficientDataException = InsufficientDataError
