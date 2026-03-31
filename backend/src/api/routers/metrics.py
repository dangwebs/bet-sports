from fastapi import APIRouter, Depends
from src.application.services.metrics_baseline import compute_baseline
from src.dependencies import get_persistence_repository

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/baseline90d")
def baseline_90d(persistence_repo=Depends(get_persistence_repository)):
    result = compute_baseline(persistence_repo, days=90)
    return result
