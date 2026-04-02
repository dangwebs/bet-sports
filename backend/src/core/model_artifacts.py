from __future__ import annotations

import logging
from pathlib import Path

from src.core.constants import ML_MODEL_FILENAME
from src.core.paths import BACKEND_ROOT


def get_model_artifact_paths() -> list[Path]:
    """Return the local ML artifact paths that must not survive a run."""
    model_paths = [BACKEND_ROOT / ML_MODEL_FILENAME]
    model_paths.extend(sorted((BACKEND_ROOT / "ml_models").glob("*.joblib")))
    return model_paths


def cleanup_model_artifacts(logger: logging.Logger) -> None:
    """Remove persisted ML artifacts without interrupting the caller."""
    removed_count = 0
    failed_count = 0

    for artifact_path in get_model_artifact_paths():
        if not artifact_path.exists():
            continue

        try:
            artifact_path.unlink()
            removed_count += 1
            logger.info("Removed local ML artifact: %s", artifact_path)
        except OSError as exc:
            failed_count += 1
            logger.warning(
                "Failed to remove local ML artifact %s: %s",
                artifact_path,
                exc,
            )

    if removed_count == 0 and failed_count == 0:
        logger.info("No local ML artifacts found to remove.")
        return

    logger.info(
        "Local ML artifact cleanup finished. removed=%s failed=%s",
        removed_count,
        failed_count,
    )
