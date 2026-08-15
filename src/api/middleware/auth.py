"""
src.api.middleware.auth — API key authentication for REST and WebSocket.

Provides a FastAPI dependency for REST routes and a standalone verifier
for WebSocket connections. If NEXUS_API_SECRET is not configured, auth
is bypassed (development mode).
"""

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from src.core.config import settings, audit_logger

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(_api_key_header)):
    """FastAPI dependency that enforces API key auth on REST endpoints.
    If NEXUS_API_SECRET is not configured, auth is bypassed (dev mode)."""
    if not settings.NEXUS_API_SECRET:
        return  # No secret configured — allow all (development mode)
    if not api_key or api_key != settings.NEXUS_API_SECRET:
        audit_logger.warning("REST auth failed — invalid or missing API key")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Provide a valid X-API-Key header.",
        )


def verify_ws_token(token: str | None) -> bool:
    """Validates WebSocket auth token. Returns True if auth passes."""
    if not settings.NEXUS_API_SECRET:
        return True  # No secret configured — allow all (development mode)
    return token == settings.NEXUS_API_SECRET
