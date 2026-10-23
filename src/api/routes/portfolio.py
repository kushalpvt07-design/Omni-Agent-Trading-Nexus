"""
src.api.routes.portfolio — Per-user Portfolio REST endpoints.
"""

import asyncio
from fastapi import APIRouter, Query, Depends

from src.api.middleware.auth import get_current_user
from src.persistence.user_portfolio import (
    build_full_portfolio_summary,
    get_portfolio_history,
    get_portfolio_change,
    get_user_trades,
)

router = APIRouter(tags=["Portfolio"])


@router.get("/api/v1/portfolio")
async def get_portfolio(user=Depends(get_current_user)):
    """Return current portfolio holdings with live USD-normalized market data."""
    return await asyncio.to_thread(build_full_portfolio_summary, user["user_id"])


@router.get("/api/v1/portfolio/history")
async def get_portfolio_history_endpoint(
    timeframe: str = Query(default="1D", pattern="^(1D|1M|1Y|ALL)$"),
    user=Depends(get_current_user),
):
    """Return historical portfolio value snapshots for charting."""
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
