"""Canonicalize team names using a shared alias table."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_ALIAS_MAP: Dict[str, str] = {}


def _ensure_loaded() -> None:
    global _ALIAS_MAP
    if _ALIAS_MAP:
        return
    try:
        repo_root = Path(__file__).resolve().parents[3]
        aliases_path = repo_root / "backend" / "data" / "team_short_names.json"
        if aliases_path.exists():
            with aliases_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                # store lowercase keys for robust lookup
                _ALIAS_MAP = {k.lower(): v for k, v in data.items()}
    except Exception:
        _ALIAS_MAP = {}


def canonicalize(name: str) -> str:
    """Return canonical short name if known, otherwise original input.

    The lookup is case-insensitive.
    """
    if not name:
        return name
    _ensure_loaded()
    return _ALIAS_MAP.get(name.strip().lower(), name)
