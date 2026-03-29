"""Seguridad de la API: autenticación por API key y dependencia para endpoints administrativos."""

import os
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")


async def require_admin_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """Dependency que exige API key válida para endpoints administrativos.

    Lanza HTTPException 503 si la key no está configurada en el servidor.
    Lanza HTTPException 403 si la key es inválida.
    """
    if not _ADMIN_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Admin API key not configured on server",
        )
    if api_key != _ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    return api_key
