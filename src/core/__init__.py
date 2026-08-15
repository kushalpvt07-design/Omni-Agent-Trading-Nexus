"""
src.core — Centralized configuration, logging, and security utilities.

Modules:
    config    — Settings class, environment variable loading, structured logging setup
    security  — Input sanitization for untrusted user directives

Public API:
    settings       — Singleton Settings instance with all app configuration
    logger         — Main application logger ("omni-nexus")
    audit_logger   — Dedicated audit trail logger ("omni-nexus.audit")
    sanitize_raw_input — Clean and truncate untrusted user text
"""

from src.core.config import settings, logger, audit_logger
from src.core.security import sanitize_raw_input

__all__ = [
    "settings",
    "logger",
    "audit_logger",
    "sanitize_raw_input",
]
