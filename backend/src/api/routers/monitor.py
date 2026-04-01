from typing import Any, Dict

from fastapi import APIRouter, Depends
from src.api.security import require_admin_key
from src.dependencies import get_persistence_repository

router = APIRouter(prefix="/admin/monitor", tags=["admin", "monitor"])


@router.get("/backlog")
def backlog(
    admin_key: str = Depends(require_admin_key),
    persistence_repo: Any = Depends(get_persistence_repository),
) -> Dict[str, Any]:
    """Return a simple backlog count for pending/unlabeled predictions."""
    try:
        coll = persistence_repo.match_predictions
        # prefer efficient count_documents if available
        try:
            pending = coll.count_documents({"labeled": {"$ne": True}})
        except Exception:
            # fallback iterate
            pending = sum(1 for _ in coll.find({"labeled": {"$ne": True}}))
        return {"pending_predictions": int(pending)}
    except Exception as exc:
        return {"error": str(exc)}
