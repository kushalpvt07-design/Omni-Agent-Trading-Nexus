"""
src.api.routes.portfolio — Portfolio Ledger REST endpoint.

Provides a GET endpoint that returns the current portfolio state
(cash balance, positions with live prices and market values).
"""

import asyncio

from fastapi import APIRouter

from src.agents.risk_agent import get_ledger_data
from src.core.config import logger
from utils import get_live_asset_data

router = APIRouter(tags=["Portfolio"])


@router.get("/api/v1/portfolio")
async def get_portfolio():
    """Return current portfolio holdings with live market data."""
    ledger = get_ledger_data()
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

    return {
        "cash": round(cash, 2),
        "total_value": round(cash + total_market_value, 2),
        "positions": positions,
    }
