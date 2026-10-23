"""
src.persistence.user_portfolio — Per-user portfolio operations.

All ledger, position, trade, and snapshot operations are scoped by user_id.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from src.persistence.database import get_db

logger = logging.getLogger("omni-nexus.user-portfolio")

MIN_SNAPSHOT_INTERVAL_SECONDS = 30
DEFAULT_STARTING_CASH = 100000.0


def create_user_ledger(user_id: int, starting_cash: float = DEFAULT_STARTING_CASH) -> None:
    """Initialize the ledger row for a newly registered user."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_ledger (user_id, cash) VALUES (?, ?)",
            (user_id, starting_cash),
        )


def get_user_ledger(user_id: int) -> dict:
    """Get the user's current cash balance and raw position share counts."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT cash FROM user_ledger WHERE user_id = ?", (user_id,)
        ).fetchone()

        cash = float(row["cash"]) if row else DEFAULT_STARTING_CASH

        positions_rows = conn.execute(
            "SELECT ticker, shares FROM user_positions WHERE user_id = ? AND shares > 1e-6",
            (user_id,),
        ).fetchall()

        positions = {r["ticker"]: float(r["shares"]) for r in positions_rows}

    return {"cash": cash, "positions": positions}


def build_full_portfolio_summary(user_id: int) -> dict:
    """Build the complete portfolio payload (cash, total_value, and enriched positions array)
    used by both GET /api/v1/portfolio and WebSocket portfolio_update events (BUG-002)."""
    from src.core.market_data import get_latest_prices

    ledger = get_user_ledger(user_id)
    cash = ledger.get("cash", 0.0)
    raw_positions = ledger.get("positions", {})

    tickers_to_price = [t for t, s in raw_positions.items() if s > 1e-6]
    # Convert Indian stock prices to USD so total_value and market_value match the USD cash ledger (BUG-003)
    live_prices_usd = (
        get_latest_prices(tickers_to_price, convert_indian_to_usd=True)
        if tickers_to_price
        else {}
    )

    positions = []
    total_market_value = 0.0

    with get_db() as conn:
        for ticker, shares in raw_positions.items():
            if shares <= 1e-6:
                continue

            pos_row = conn.execute(
                "SELECT avg_cost FROM user_positions WHERE user_id = ? AND ticker = ?",
                (user_id, ticker),
            ).fetchone()
            avg_cost = (
                float(pos_row["avg_cost"])
                if pos_row and pos_row["avg_cost"]
                else 0.0
            )

            current_price = live_prices_usd.get(ticker, 0.0)
            if current_price <= 0.0:
                current_price = avg_cost

            market_value = round(shares * current_price, 2)
            total_market_value += market_value

            positions.append(
                {
                    "ticker": ticker,
                    "shares": round(shares, 4),
                    "current_price": round(current_price, 2),
                    "avg_cost": round(avg_cost, 4),
                    "market_value": market_value,
                }
            )

    total_value = round(cash + total_market_value, 2)
    record_portfolio_snapshot(user_id, total_value, cash)

    return {
        "cash": round(cash, 2),
        "total_value": total_value,
        "positions": positions,
    }


def update_user_ledger(
    user_id: int,
    action: str,
    ticker: str,
    shares: float,
    price: float,
    reasoning: str | None = None,
    alpaca_order_id: str | None = None,
) -> dict:
    """Record a trade and update the user's cash & positions in an atomic transaction."""
    total_value = round(shares * price, 2)

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            "SELECT cash FROM user_ledger WHERE user_id = ?", (user_id,)
        ).fetchone()
        cash = float(row["cash"]) if row else DEFAULT_STARTING_CASH

        pos_row = conn.execute(
            "SELECT shares, avg_cost FROM user_positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        current_shares = float(pos_row["shares"]) if pos_row else 0.0
        current_avg_cost = float(pos_row["avg_cost"]) if pos_row else 0.0

        if action == "BUY":
            new_cash = cash - total_value
            new_shares = current_shares + shares
            if new_shares > 0:
                new_avg_cost = (
                    (current_shares * current_avg_cost) + (shares * price)
                ) / new_shares
            else:
                new_avg_cost = price

            if new_cash < -1e-6:
                conn.execute("ROLLBACK")
                logger.warning(
                    "Ledger invariant violated: BUY would overdraft user=%d (cash=%.2f, cost=%.2f)",
                    user_id, cash, total_value,
                )
                raise ValueError(
                    f"Insufficient cash: ${cash:,.2f} available, ${total_value:,.2f} required."
                )
            new_cash = max(0.0, new_cash)

        elif action == "SELL":
            if shares > current_shares + 1e-6:
                conn.execute("ROLLBACK")
                logger.warning(
                    "Ledger invariant violated: SELL %.4f > owned %.4f for user=%d %s",
                    shares, current_shares, user_id, ticker,
                )
                raise ValueError(
                    f"Oversell rejected: tried to sell {shares:.4f} shares but only {current_shares:.4f} owned."
                )
            new_cash = cash + total_value
            new_shares = max(0.0, current_shares - shares)
            new_avg_cost = current_avg_cost
        else:
            new_cash = cash
            new_shares = current_shares
            new_avg_cost = current_avg_cost

        conn.execute(
            """INSERT INTO user_ledger (user_id, cash) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET cash = excluded.cash""",
            (int(user_id), round(new_cash, 2)),
        )

        # Cleanly delete position if remaining shares are floating-point dust <= 1e-6 (BUG-017)
        if new_shares > 1e-6:
            conn.execute(
                """INSERT INTO user_positions (user_id, ticker, shares, avg_cost)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, ticker) DO UPDATE SET
                     shares = excluded.shares,
                     avg_cost = excluded.avg_cost""",
                (user_id, ticker, round(new_shares, 6), round(new_avg_cost, 4)),
            )
        else:
            conn.execute(
                "DELETE FROM user_positions WHERE user_id = ? AND ticker = ?",
                (user_id, ticker),
            )

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


def record_portfolio_snapshot(user_id: int, total_value: float, cash: float) -> None:
    """Record a portfolio value snapshot with rate limiting, unless value changed > 0.01% (BUG-017)."""
    with get_db() as conn:
        last = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()

        if last:
            try:
                last_ts = datetime.fromisoformat(last["recorded_at"])
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - last_ts).total_seconds()
                prev_val = float(last["total_value"] or 0.0)
                pct_diff = abs(total_value - prev_val) / prev_val if prev_val > 0 else 1.0

                if elapsed < MIN_SNAPSHOT_INTERVAL_SECONDS and pct_diff <= 0.0001:
                    return
            except Exception as e:
                logger.debug("Snapshot timestamp parse warning: %s", e)

        conn.execute(
            "INSERT INTO portfolio_snapshots (user_id, total_value, cash, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (
                user_id,
                round(total_value, 2),
                round(cash, 2),
                datetime.now(timezone.utc).isoformat(),
            ),
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


def get_portfolio_history(user_id: int, timeframe: str = "ALL") -> List[Dict[str, Any]]:
    """Return portfolio history using Last-Observation-Carried-Forward (LOCF) step function."""
    now = datetime.now(timezone.utc)

    timeframe_config = {
        "1D":  {"delta": timedelta(days=1),   "points": 48},
        "1M":  {"delta": timedelta(days=30),  "points": 60},
        "1Y":  {"delta": timedelta(days=365), "points": 52},
        "ALL": {"delta": None,                "points": 60},
    }

    config = timeframe_config.get(timeframe, timeframe_config["1D"])
    num_points = config["points"]

    raw = _get_raw_snapshots(user_id, timeframe)

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

    if config["delta"] is not None:
        window_start = now - config["delta"]
    else:
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
            if (now - window_start).total_seconds() < 86400:
                window_start = now - timedelta(days=1)
        else:
            window_start = now - timedelta(days=1)

    baseline_value = DEFAULT_STARTING_CASH
    baseline_cash = DEFAULT_STARTING_CASH

    with get_db() as conn:
        prior = conn.execute(
            "SELECT total_value, cash FROM portfolio_snapshots "
            "WHERE user_id = ? AND recorded_at < ? ORDER BY recorded_at DESC LIMIT 1",
            (user_id, window_start.isoformat()),
        ).fetchone()
        if prior:
            baseline_value = prior["total_value"]
            baseline_cash = prior["cash"]

    total_seconds = max((now - window_start).total_seconds(), 1.0)
    interval_seconds = total_seconds / max(num_points - 1, 1)

    timeline: List[datetime] = []
    for i in range(num_points):
        t = window_start + timedelta(seconds=interval_seconds * i)
        timeline.append(t)

    result: List[Dict[str, Any]] = []
    for t in timeline:
        current_value = baseline_value
        current_cash = baseline_cash
        for snap in snapshots:
            if snap["dt"] <= t:
                current_value = snap["total_value"]
                current_cash = snap["cash"]
            else:
                break

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
