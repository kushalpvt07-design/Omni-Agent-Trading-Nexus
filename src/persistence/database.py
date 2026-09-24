"""
src.persistence.database — SQLite database for user accounts and per-user portfolios.

Manages the nexus_users.db database lifecycle:
  - Connection pooling with WAL journal mode
  - Schema initialization on startup
  - Context manager for transactional access
"""

import os
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger("omni-nexus.database")

DB_FILE = os.getenv("NEXUS_DB_FILE", "nexus_users.db")

_SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    starting_cash REAL   NOT NULL DEFAULT 100000.0,
    created_at    TEXT   NOT NULL DEFAULT (datetime('now'))
);

-- Per-user ledger (current cash balance)
CREATE TABLE IF NOT EXISTS user_ledger (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cash    REAL    NOT NULL DEFAULT 100000.0,
    UNIQUE(user_id)
);

-- Per-user positions (one row per ticker per user)
CREATE TABLE IF NOT EXISTS user_positions (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker   TEXT    NOT NULL,
    shares   REAL    NOT NULL DEFAULT 0.0,
    avg_cost REAL    NOT NULL DEFAULT 0.0,
    UNIQUE(user_id, ticker)
);

-- Complete trade log (every BUY/SELL/HOLD recorded)
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker          TEXT    NOT NULL,
    action          TEXT    NOT NULL,
    shares          REAL    NOT NULL DEFAULT 0.0,
    price           REAL    NOT NULL DEFAULT 0.0,
    total_value     REAL    NOT NULL DEFAULT 0.0,
    reasoning       TEXT,
    alpaca_order_id TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Portfolio value snapshots (for the chart)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_value REAL    NOT NULL,
    cash        REAL    NOT NULL,
    recorded_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for fast user-scoped queries
CREATE INDEX IF NOT EXISTS idx_trades_user      ON trades(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_user   ON user_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_user   ON portfolio_snapshots(user_id, recorded_at DESC);
"""


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager that yields a connection, commits on success, rolls back on error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Create all tables and indexes if they don't exist. Called during app startup."""
    with get_db() as conn:
        conn.executescript(_SCHEMA_SQL)
    logger.info("Database initialized: %s", DB_FILE)
