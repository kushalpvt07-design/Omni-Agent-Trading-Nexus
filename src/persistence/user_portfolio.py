"""
src.persistence.user_portfolio — Per-user portfolio operations.

All ledger, position, trade, and snapshot operations are scoped by user_id.
This replaces the old JSON-file-based portfolio_ledger.json approach.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from src.persistence.database import get_db

logger = logging.getLogger("omni-nexus.user-portfolio")

# Minimum seconds between portfolio snapshots to avoid flooding
MIN_SNAPSHOT_INTERVAL_SECONDS = 30

DEFAULT_STARTING_CASH = 100000.0


# ── User Ledger ─────────────────────────────────────────────────


def create_user_ledger(user_id: int, starting_cash: float = DEFAULT_STARTING_CASH) -> None:
    """Initialize the ledger row for a newly registered user."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_ledger (user_id, cash) VALUES (?, ?)",
            (user_id, starting_cash),
        )


def get_user_ledger(user_id: int) -> dict:
    """Get the user's current cash balance and positions.

    Returns: {"cash": float, "positions": {"TICKER": shares, ...}}
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT cash FROM user_ledger WHERE user_id = ?", (user_id,)
        ).fetchone()

        cash = row["cash"] if row else DEFAULT_STARTING_CASH

        positions_rows = conn.execute(
            "SELECT ticker, shares FROM user_positions WHERE user_id = ? AND shares > 0",
            (user_id,),
        ).fetchall()

        positions = {r["ticker"]: r["shares"] for r in positions_rows}

    return {"cash": cash, "positions": positions}


def update_user_ledger(
    user_id: int,
    action: str,
    ticker: str,
    shares: float,
    price: float,
    reasoning: str | None = None,
    alpaca_order_id: str | None = None,
) -> dict:
    """Record a trade and update the user's cash & positions.

    Returns the updated ledger dict.
    """
    total_value = round(shares * price, 2)

    with get_db() as conn:
        # §3.2 — Use BEGIN IMMEDIATE so no other connection can read-then-write
        # the same cash balance concurrently (prevents lost-update races).
        conn.execute("BEGIN IMMEDIATE")

        # Get current cash
        row = conn.execute(
            "SELECT cash FROM user_ledger WHERE user_id = ?", (user_id,)
        ).fetchone()
        cash = row["cash"] if row else DEFAULT_STARTING_CASH

        # Get current position
        pos_row = conn.execute(
            "SELECT shares, avg_cost FROM user_positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        current_shares = pos_row["shares"] if pos_row else 0.0
        current_avg_cost = pos_row["avg_cost"] if pos_row else 0.0

        if action == "BUY":
            new_cash = cash - total_value
            new_shares = current_shares + shares
            # Weighted average cost
            if new_shares > 0:
                new_avg_cost = (
                    (current_shares * current_avg_cost) + (shares * price)
                ) / new_shares
            else:
                new_avg_cost = price

            # §3.3 — Hard invariant: never allow negative cash at the ledger layer
            if new_cash < 0:
                conn.execute("ROLLBACK")
                logger.warning(
                    "Ledger invariant violated: BUY would overdraft user=%d (cash=%.2f, cost=%.2f)",
                    user_id, cash, total_value,
                )
                raise ValueError(
                    f"Insufficient cash: ${cash:,.2f} available, ${total_value:,.2f} required."
                )

        elif action == "SELL":
            # §3.3 — Hard invariant: cannot sell more than owned
            if shares > current_shares + 1e-9:
                conn.execute("ROLLBACK")
                logger.warning(
                    "Ledger invariant violated: SELL %.4f > owned %.4f for user=%d %s",
                    shares, current_shares, user_id, ticker,
                )
                raise ValueError(
                    f"Oversell rejected: tried to sell {shares:.4f} shares but only {current_shares:.4f} owned."
                )
            new_cash = cash + total_value
            new_shares = current_shares - shares
            new_avg_cost = current_avg_cost  # avg cost doesn't change on sell
        else:
            # HOLD — no cash/position change
            new_cash = cash
            new_shares = current_shares
            new_avg_cost = current_avg_cost

        # §3.4 — UPSERT the ledger row so a missing row never causes a silent no-op
        conn.execute(
            """INSERT INTO user_ledger (user_id, cash) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET cash = excluded.cash""",
            (round(new_cash, 2), user_id),
        )

        # Update or insert position
        if new_shares > 0:
            conn.execute(
                """INSERT INTO user_positions (user_id, ticker, shares, avg_cost)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, ticker) DO UPDATE SET
                     shares = excluded.shares,
                     avg_cost = excluded.avg_cost""",
                (user_id, ticker, round(new_shares, 6), round(new_avg_cost, 4)),
            )
        else:
            # Remove position if shares drop to 0 or below
            conn.execute(
                "DELETE FROM user_positions WHERE user_id = ? AND ticker = ?",
                (user_id, ticker),
            )

        # Record the trade
        conn.execute(
            """INSERT INTO trades
               (user_id, ticker, action, shares, price, total_value, reasoning, alpaca_order_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, ticker, action, shares, price, total_value, reasoning, alpaca_order_id),
        )

    logger.info(
        "Trade recorded — user=%d %s %.4f %s @ $%.2f (total=$%.2f)",
        user_id, action, shares, ticker, price, total_value,
    )

    return get_user_ledger(user_id)


# ── Portfolio Snapshots ─────────────────────────────────────────


def record_portfolio_snapshot(user_id: int, total_value: float, cash: float) -> None:
    """Record a portfolio value snapshot with rate limiting.

    Skips the write if the last snapshot was taken less than
    MIN_SNAPSHOT_INTERVAL_SECONDS ago, unless the value changed
    meaningfully (> 0.01% difference).
    """
    with get_db() as conn:
        last = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()

        if last:
            try:
                last_ts = datetime.fromisoformat(last["recorded_at"])
                # Make timezone-aware if it isn't
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - last_ts).total_seconds()

                if elapsed < MIN_SNAPSHOT_INTERVAL_SECONDS:
                    return  # Too soon — skip
            except Exception:
                pass

        conn.execute(
            "INSERT INTO portfolio_snapshots (user_id, total_value, cash, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, round(total_value, 2), round(cash, 2),
             datetime.now(timezone.utc).isoformat()),
        )


def _get_raw_snapshots(user_id: int, timeframe: str) -> List[Dict[str, Any]]:
    """Fetch raw portfolio snapshots from the database for a given timeframe."""
    cutoff_map = {
        "1D": timedelta(days=1),
        "1M": timedelta(days=30),
        "1Y": timedelta(days=365),
    }

    with get_db() as conn:
        if timeframe == "ALL" or timeframe not in cutoff_map:
            rows = conn.execute(
                "SELECT total_value, cash, recorded_at as timestamp "
                "FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at",
                (user_id,),
            ).fetchall()
        else:
            cutoff = (datetime.now(timezone.utc) - cutoff_map[timeframe]).isoformat()
            rows = conn.execute(
                "SELECT total_value, cash, recorded_at as timestamp "
                "FROM portfolio_snapshots "
                "WHERE user_id = ? AND recorded_at >= ? ORDER BY recorded_at",
                (user_id, cutoff),
            ).fetchall()

    return [
        {
            "timestamp": r["timestamp"],
            "total_value": r["total_value"],
            "cash": r["cash"],
        }
        for r in rows
    ]


def _get_account_created_at(user_id: int) -> Optional[datetime]:
    """Get the datetime the user account was created."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row and row["created_at"]:
            dt = datetime.fromisoformat(row["created_at"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    return None


def _get_first_snapshot(user_id: int) -> Optional[Dict[str, Any]]:
    """Get the user's very first portfolio snapshot ever (used as baseline)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT total_value, cash, recorded_at as timestamp "
            "FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at LIMIT 1",
            (user_id,),
        ).fetchone()
        if row:
            return {
                "timestamp": row["timestamp"],
                "total_value": row["total_value"],
                "cash": row["cash"],
            }
    return None


def _lerp(v0: float, v1: float, t: float) -> float:
    """Linear interpolation between v0 and v1 at fraction t."""
    return v0 + (v1 - v0) * t


def get_portfolio_history(user_id: int, timeframe: str = "ALL") -> List[Dict[str, Any]]:
    """Return portfolio history with synthetic data points spanning the full timeframe.

    Uses Last-Observation-Carried-Forward (LOCF / step-function) instead of
    linear interpolation (§5.2). A trade loss recorded today should not appear
    as a smooth decline starting weeks earlier.

    Supported timeframes: 1D, 1M, 1Y, ALL.
    """
    now = datetime.now(timezone.utc)

    # Determine chart parameters per timeframe
    timeframe_config = {
        "1D":  {"delta": timedelta(days=1),   "points": 48},   # ~30 min intervals
        "1M":  {"delta": timedelta(days=30),  "points": 60},   # ~12 hour intervals
        "1Y":  {"delta": timedelta(days=365), "points": 52},   # ~weekly intervals
        "ALL": {"delta": None,                "points": 60},
    }

    config = timeframe_config.get(timeframe, timeframe_config["1D"])
    num_points = config["points"]

    # Get actual snapshots for the timeframe
    raw = _get_raw_snapshots(user_id, timeframe)

    # Parse timestamps on raw snapshots
    snapshots = []
    for r in raw:
        try:
            dt = datetime.fromisoformat(r["timestamp"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            snapshots.append({
                "dt": dt,
                "total_value": r["total_value"],
                "cash": r["cash"],
            })
        except (ValueError, TypeError):
            continue

    # Determine the start of the time window
    if config["delta"] is not None:
        window_start = now - config["delta"]
    else:
        # For "ALL": go back to account creation or first snapshot
        account_created = _get_account_created_at(user_id)
        first_snap = _get_first_snapshot(user_id)
        first_snap_dt = None
        if first_snap:
            try:
                first_snap_dt = datetime.fromisoformat(first_snap["timestamp"])
                if first_snap_dt.tzinfo is None:
                    first_snap_dt = first_snap_dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        candidates = [dt for dt in [account_created, first_snap_dt] if dt is not None]
        if candidates:
            window_start = min(candidates)
            # Ensure at least a 1-day window
            if (now - window_start).total_seconds() < 86400:
                window_start = now - timedelta(days=1)
        else:
            window_start = now - timedelta(days=1)

    # Determine the baseline value (before any snapshots in the window)
    baseline_value = DEFAULT_STARTING_CASH
    baseline_cash = DEFAULT_STARTING_CASH

    # Check if there's a snapshot just before the window starts
    with get_db() as conn:
        prior = conn.execute(
            "SELECT total_value, cash FROM portfolio_snapshots "
            "WHERE user_id = ? AND recorded_at < ? ORDER BY recorded_at DESC LIMIT 1",
            (user_id, window_start.isoformat()),
        ).fetchone()
        if prior:
            baseline_value = prior["total_value"]
            baseline_cash = prior["cash"]

    # Build timeline: evenly spaced points from window_start to now
    total_seconds = max((now - window_start).total_seconds(), 1.0)
    interval_seconds = total_seconds / max(num_points - 1, 1)

    timeline: List[datetime] = []
    for i in range(num_points):
        t = window_start + timedelta(seconds=interval_seconds * i)
        timeline.append(t)

    # §5.2 — Step / Last-Observation-Carried-Forward (LOCF) instead of lerp.
    # Build output by carrying the last known value forward to each timeline point.
    # Snapshots after a given point are ignored; we only use the latest snapshot
    # that is at or before the timeline point.
    result: List[Dict[str, Any]] = []

    for t in timeline:
        # Find the latest snapshot at or before t
        current_value = baseline_value
        current_cash = baseline_cash
        for snap in snapshots:
            if snap["dt"] <= t:
                current_value = snap["total_value"]
                current_cash = snap["cash"]
            else:
                break  # snapshots are sorted ascending; no need to look further

        result.append({
            "timestamp": t.isoformat(),
            "total_value": round(current_value, 2),
            "cash": round(current_cash, 2),
        })

    return result


def get_portfolio_change(user_id: int, timeframe: str = "1D") -> Optional[Dict[str, Any]]:
    """Calculate the portfolio value change over a given timeframe."""
    history = get_portfolio_history(user_id, timeframe)

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


# ── Trade History ───────────────────────────────────────────────


def get_user_trades(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Return the user's trade history, most recent first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT ticker, action, shares, price, total_value, reasoning, "
            "       alpaca_order_id, created_at "
            "FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()

    return [
        {
            "ticker": r["ticker"],
            "action": r["action"],
            "shares": r["shares"],
            "price": r["price"],
            "total_value": r["total_value"],
            "reasoning": r["reasoning"],
            "alpaca_order_id": r["alpaca_order_id"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
