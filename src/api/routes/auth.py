"""
src.api.routes.auth — User registration and login endpoints.

Provides:
  POST /api/v1/auth/register — Create a new user account
  POST /api/v1/auth/login    — Authenticate and return JWT
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import bcrypt as _bcrypt
from jose import jwt

from src.core.config import settings, logger, audit_logger
from src.persistence.database import get_db
from src.persistence.user_portfolio import create_user_ledger

router = APIRouter(tags=["Authentication"])

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


def _get_jwt_secret() -> str:
    """Return the JWT signing secret, falling back to a dev default."""
    return settings.NEXUS_API_SECRET or "dev-secret-change-me"


def _create_token(user_id: int, username: str) -> str:
    """Create a signed JWT token for the given user."""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


# ── Request / Response Models ───────────────────────────────────


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: dict


# ── Endpoints ───────────────────────────────────────────────────


@router.post("/api/v1/auth/register")
async def register(body: AuthRequest) -> AuthResponse:
    """Create a new user account.

    Returns a JWT token and user info on success.
    Raises 409 if the username already exists.
    """
    password_hash = _bcrypt.hashpw(
        body.password.encode("utf-8"), _bcrypt.gensalt()
    ).decode("utf-8")

    with get_db() as conn:
        # Check if username already exists
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (body.username,)
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Username already taken. Please choose a different one.",
            )

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (body.username, password_hash),
        )
        user_id = cursor.lastrowid

    # Initialize the user's ledger with starting cash
    create_user_ledger(user_id)

    token = _create_token(user_id, body.username)

    audit_logger.info("New user registered: %s (id=%d)", body.username, user_id)

    return AuthResponse(
        token=token,
        user={"id": user_id, "username": body.username},
    )


@router.post("/api/v1/auth/login")
async def login(body: AuthRequest) -> AuthResponse:
    """Authenticate a user and return a JWT token.

    Raises 401 if credentials are invalid.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (body.username,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not _bcrypt.checkpw(
        body.password.encode("utf-8"),
        row["password_hash"].encode("utf-8"),
    ):
        audit_logger.warning("Failed login attempt for user: %s", body.username)
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = _create_token(row["id"], row["username"])

    audit_logger.info("User logged in: %s (id=%d)", row["username"], row["id"])

    return AuthResponse(
        token=token,
        user={"id": row["id"], "username": row["username"]},
    )
