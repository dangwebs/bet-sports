from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from src.api.security import require_admin_key
from src.application.services.labeler import reconcile_predictions
from src.dependencies import get_persistence_repository

router = APIRouter(prefix="/admin/labeler", tags=["admin", "labeler"])


@router.post("/dry-run")
def labeler_dry_run(
    window: str = Query("90d"),
    admin_key: str = Depends(require_admin_key),
    persistence_repo: Any = Depends(get_persistence_repository),
) -> Dict[str, Any]:
    # window parsing: accept '90d' -> 90
    try:
        days = int(window.rstrip("d"))
    except Exception:
        days = 90
    report = reconcile_predictions(persistence_repo, window_days=days, dry_run=True)
    return {"status": "dry-run", "report": report}


@router.post("/run")
def labeler_run(
    window: str = Query("90d"),
    admin_key: str = Depends(require_admin_key),
    persistence_repo: Any = Depends(get_persistence_repository),
) -> Dict[str, Any]:
    try:
        days = int(window.rstrip("d"))
    except Exception:
        days = 90
    report = reconcile_predictions(persistence_repo, window_days=days, dry_run=False)
    return {"status": "completed", "report": report}
