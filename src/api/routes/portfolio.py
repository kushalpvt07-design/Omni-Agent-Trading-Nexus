"""
src.api.routes.portfolio — Per-user Portfolio REST endpoints.

Provides:
  GET  /api/v1/portfolio          — Current portfolio state with live prices (user-scoped)
  GET  /api/v1/portfolio/history  — Historical portfolio value snapshots (user-scoped)
  GET  /api/v1/portfolio/trades   — User's trade history
"""

import asyncio

from fastapi import APIRouter, Query, Depends

from src.api.middleware.auth import get_current_user
from src.core.config import logger
from src.core.market_data import get_latest_prices
from src.persistence.database import get_db
from src.persistence.user_portfolio import (
    get_user_ledger,
    record_portfolio_snapshot,
    get_portfolio_history,
    get_portfolio_change,
    get_user_trades,
)

router = APIRouter(tags=["Portfolio"])


@router.get("/api/v1/portfolio")
async def get_portfolio(user=Depends(get_current_user)):
    """Return current portfolio holdings with live Alpaca market data for the authenticated user."""
    user_id = user["user_id"]
    ledger = get_user_ledger(user_id)
    cash = ledger.get("cash", 0.0)
    raw_positions = ledger.get("positions", {})

    # Collect all tickers that need pricing
    tickers_to_price = [t for t, s in raw_positions.items() if s > 0]

    # Fetch all live prices in a single Alpaca API call
    live_prices = {}
    if tickers_to_price:
        live_prices = await asyncio.to_thread(get_latest_prices, tickers_to_price)

    positions = []
    total_market_value = 0.0

    for ticker, shares in raw_positions.items():
        if shares <= 0:
            continue

        current_price = live_prices.get(ticker, 0.0)

        # Fallback: use avg_cost when Alpaca price is unavailable
        if current_price == 0.0:
            with get_db() as conn:
                pos_row = conn.execute(
                    "SELECT avg_cost FROM user_positions WHERE user_id = ? AND ticker = ?",
                    (user_id, ticker),
                ).fetchone()
                if pos_row and pos_row["avg_cost"]:
                    current_price = pos_row["avg_cost"]

        market_value = round(shares * current_price, 2)
        total_market_value += market_value

        positions.append({
            "ticker": ticker,
            "shares": round(shares, 4),
            "current_price": round(current_price, 2),
            "market_value": market_value,
        })

    total_value = round(cash + total_market_value, 2)

    # Record a snapshot of total portfolio value for the history chart
    record_portfolio_snapshot(user_id, total_value, cash)

    return {
        "cash": round(cash, 2),
        "total_value": total_value,
        "positions": positions,
    }


@router.get("/api/v1/portfolio/history")
async def get_portfolio_history_endpoint(
    timeframe: str = Query(default="1D", pattern="^(1D|1M|1Y|ALL)$"),
    user=Depends(get_current_user),
):
    """Return historical portfolio value snapshots for charting.

    Query params:
        timeframe — One of: 1D, 1M, 1Y, ALL (default: 1D)
    """
    user_id = user["user_id"]
    history = get_portfolio_history(user_id, timeframe)
    change = get_portfolio_change(user_id, timeframe)

    return {
        "timeframe": timeframe,
        "data_points": history,
        "change": change,
    }


@router.get("/api/v1/portfolio/trades")
async def get_trades_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(get_current_user),
):
    """Return the authenticated user's trade history."""
    return {
        "trades": get_user_trades(user["user_id"], limit),
    }
