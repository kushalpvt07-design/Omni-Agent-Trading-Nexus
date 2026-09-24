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
from src.persistence.user_portfolio import (
    get_user_ledger,
    record_portfolio_snapshot,
    get_portfolio_history,
    get_portfolio_change,
    get_user_trades,
)
from utils import get_live_asset_data

router = APIRouter(tags=["Portfolio"])


@router.get("/api/v1/portfolio")
async def get_portfolio(user=Depends(get_current_user)):
    """Return current portfolio holdings with live market data for the authenticated user."""
    user_id = user["user_id"]
    ledger = get_user_ledger(user_id)
    cash = ledger.get("cash", 0.0)
    raw_positions = ledger.get("positions", {})

    positions = []
    total_market_value = 0.0

    for ticker, shares in raw_positions.items():
        if shares <= 0:
            continue

        current_price = 0.0
        try:
            live_data = await asyncio.to_thread(get_live_asset_data, ticker)
            if live_data and live_data.get("current_price"):
                current_price = live_data["current_price"]
        except Exception as e:
            logger.warning("Failed to fetch live price for %s: %s", ticker, e)

        market_value = round(shares * current_price, 2)
        total_market_value += market_value

        positions.append({
            "ticker": ticker,
            "shares": round(shares, 4),
            "current_price": current_price,
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
