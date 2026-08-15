"""
src.core.config — Centralized application configuration.

All environment variables, constants, and app-wide settings are defined here.
No other module should call os.getenv() directly.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ── API Key Normalization ───────────────────────────────────────
if "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# ── Structured Logging ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("omni-nexus")
audit_logger = logging.getLogger("omni-nexus.audit")


# ── Application Settings ────────────────────────────────────────
class Settings:
    """Immutable application configuration loaded from environment."""

    APP_TITLE: str = "Omni-Agent Trading Nexus API"
    APP_DESCRIPTION: str = "Backend engine for the autonomous trading swarm."
    APP_VERSION: str = "1.0.0"

    # Authentication
    NEXUS_API_SECRET: str | None = os.getenv("NEXUS_API_SECRET")

    # CORS
    CORS_ORIGINS: list[str] = (
        os.getenv("CORS_ORIGINS", "").split(",")
        if os.getenv("CORS_ORIGINS")
        else [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    # Persistence
    CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "checkpoints.sqlite")
    LEDGER_FILE: str = os.getenv("LEDGER_FILE", "portfolio_ledger.json")

    # Trading
    ALPACA_API_KEY: str | None = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET_KEY: str | None = os.getenv("ALPACA_SECRET_KEY")


settings = Settings()

# Startup warning if auth is disabled
if not settings.NEXUS_API_SECRET:
    logger.warning(
        "NEXUS_API_SECRET is not set — all endpoints are UNPROTECTED. "
        "Set this variable in .env to enable authentication."
    )
