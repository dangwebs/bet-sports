from __future__ import annotations

from datetime import datetime
from typing import Any


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _serialize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat() + "Z"
    return str(value)


def _serialize_datetimes(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serialize_datetimes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_datetimes(v) for v in obj]
    if isinstance(obj, datetime):
        return _serialize_timestamp(obj)
    return obj
