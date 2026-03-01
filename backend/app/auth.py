"""
Remembench — Authentication Dependencies

API key-based authentication for write endpoints. Read endpoints
remain open so the frontend dashboard works without auth.

Usage:
    @router.post("/", dependencies=[Depends(require_api_key)])
    async def protected_route(...):
        ...

Set the API key via environment variable:
    REMEMBENCH_API_KEY=your-secret-key-here
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

# Header name for API key authentication
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_API_KEY_HEADER),
) -> str:
    """
    Validate the API key from the X-API-Key header.

    Returns the API key if valid, raises 401/403 otherwise.
    Used as a dependency on write endpoints (POST, PUT, DELETE).
    """
    if not settings.api_key:
        # No API key configured — running in dev mode, allow all
        return "dev-mode"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
