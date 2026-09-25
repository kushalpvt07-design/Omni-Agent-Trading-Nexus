"""
src.api.middleware.auth — JWT authentication for REST and WebSocket.

Provides:
  - get_current_user()  — FastAPI dependency for REST endpoints (extracts user from JWT)
  - verify_ws_token()   — Standalone JWT verifier for WebSocket connections
  - verify_api_key()    — Legacy API key auth (kept for backward compat)
"""

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from jose import jwt, JWTError

from src.core.config import settings, audit_logger

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT Configuration (must match auth.py)
JWT_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    """Return the JWT signing secret, falling back to a dev default."""
    return settings.NEXUS_API_SECRET or "dev-secret-change-me"


# ── JWT-based User Authentication ───────────────────────────────


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency that extracts and validates the JWT from
    the Authorization: Bearer <token> header.

    Returns: {"user_id": int, "username": str}
    Raises HTTP 401 if the token is missing, invalid, or expired.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
        )

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        username = payload.get("username")
        if user_id is None or username is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )
        return {"user_id": user_id, "username": username}
    except JWTError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )


def verify_ws_token(token: str | None) -> dict | None:
    """Validates a WebSocket JWT token.

    Returns: {"user_id": int, "username": str} on success, None on failure.
    """
    if not token:
        audit_logger.warning("WS token verification failed: no token provided")
        return None
    try:
        secret = _get_jwt_secret()
        audit_logger.info("WS token verification: secret=%s..., token=%s...", secret[:8], token[:20])
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        username = payload.get("username")
        if user_id is None or username is None:
            audit_logger.warning("WS token verification failed: missing sub or username in payload: %s", payload)
            return None
        return {"user_id": user_id, "username": username}
    except JWTError as e:
        audit_logger.warning("WS token verification failed: JWTError: %s", e)
        return None
    except Exception as e:
        audit_logger.warning("WS token verification failed: unexpected error: %s", e)
        return None


# ── Legacy API Key Authentication (kept for backward compat) ────


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
