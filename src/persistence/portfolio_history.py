"""
src.persistence.portfolio_history — Portfolio Value History Tracker.

Stores timestamped snapshots of total portfolio value so the frontend
can render a portfolio performance chart across multiple timeframes.

Storage: portfolio_history.json
Format:  [{"timestamp": "ISO-8601", "total_value": float, "cash": float}, ...]
"""

import os
import json
import logging
import tempfile
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger("omni-nexus.portfolio-history")

HISTORY_FILE = "portfolio_history.json"

# Maximum number of data points to retain (rolling window)
MAX_HISTORY_POINTS = 10000

# Minimum seconds between snapshots to avoid flooding
MIN_SNAPSHOT_INTERVAL_SECONDS = 30


def _load_history() -> List[Dict[str, Any]]:
    """Load portfolio history from disk. Returns empty list if missing or corrupt."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        logger.warning("Portfolio history file is corrupt — returning empty history")
        return []


def _save_history(history: List[Dict[str, Any]]) -> None:
    """Atomically writes history via temp-file + rename."""
    dir_name = os.path.dirname(os.path.abspath(HISTORY_FILE))
    fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=dir_name)
    try:
        with os.fdopen(fd, "w") as tmp_f:
            json.dump(history, tmp_f)
        os.replace(tmp_path, HISTORY_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def record_snapshot(total_value: float, cash: float) -> None:
    """Record a portfolio value snapshot with rate limiting.

    Skips the write if the last snapshot was taken less than
    MIN_SNAPSHOT_INTERVAL_SECONDS ago, unless the value changed
    meaningfully (> 0.01% difference).
    """
    now = datetime.now(timezone.utc)
    history = _load_history()

    # Rate limiting — skip if too recent and value hasn't changed much
    if history:
        last = history[-1]
        try:
            last_ts = datetime.fromisoformat(last["timestamp"])
            elapsed = (now - last_ts).total_seconds()
            last_value = last.get("total_value", 0.0)

            if elapsed < MIN_SNAPSHOT_INTERVAL_SECONDS:
                # Only skip if value is essentially the same
                if last_value > 0 and abs(total_value - last_value) / last_value < 0.0001:
                    return
        except Exception:
            pass

    snapshot = {
        "timestamp": now.isoformat(),
        "total_value": round(total_value, 2),
        "cash": round(cash, 2),
    }

    history.append(snapshot)

    # Trim to rolling window
    if len(history) > MAX_HISTORY_POINTS:
        history = history[-MAX_HISTORY_POINTS:]

    _save_history(history)


def get_history(timeframe: str = "ALL") -> List[Dict[str, Any]]:
    """Return portfolio history filtered by timeframe.

    Supported timeframes: 1D, 1M, 1Y, ALL.
    Returns list of {timestamp, total_value, cash} dicts.
    """
    history = _load_history()

    if not history or timeframe == "ALL":
        return history

    now = datetime.now(timezone.utc)

    cutoff_map = {
        "1D": timedelta(days=1),
        "1M": timedelta(days=30),
        "1Y": timedelta(days=365),
    }

    delta = cutoff_map.get(timeframe)
    if not delta:
        return history

    cutoff = now - delta
    filtered = []

    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= cutoff:
                filtered.append(entry)
        except Exception:
            continue

    return filtered


def get_portfolio_change(timeframe: str = "1D") -> Optional[Dict[str, Any]]:
    """Calculate the portfolio value change over a given timeframe.

    Returns dict with: start_value, current_value, change_amount, change_pct
    """
    history = get_history(timeframe)

    if len(history) < 2:
        return None

    start_value = history[0]["total_value"]
    current_value = history[-1]["total_value"]

    if start_value == 0:
        return None

    change_amount = current_value - start_value
    change_pct = (change_amount / start_value) * 100

    return {
        "start_value": round(start_value, 2),
        "current_value": round(current_value, 2),
        "change_amount": round(change_amount, 2),
        "change_pct": round(change_pct, 2),
    }
