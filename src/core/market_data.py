"""
src.core.market_data — Live market data via Alpaca + yfinance.

Routing logic:
  - Indian stocks (.NS / .BO suffix) → yfinance
  - US stocks & crypto                → Alpaca Data API (latest trade)

The ticker stored in the database is already the resolved symbol from the
parser agent (e.g. "Boeing" → "BA", "Reliance" → "RELIANCE.NS"), so we
use it directly without any further conversion.
"""

import math
import logging
from typing import Dict, Optional

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest

from src.core.config import settings

logger = logging.getLogger("omni-nexus.market-data")

# Module-level Alpaca client (initialized lazily)
_client: Optional[StockHistoricalDataClient] = None


def _is_indian_stock(ticker: str) -> bool:
    """Check if a ticker is an Indian market stock (NSE/BSE)."""
    upper = ticker.upper()
    return upper.endswith(".NS") or upper.endswith(".BO")


def _get_alpaca_client() -> Optional[StockHistoricalDataClient]:
    """Lazily initialize the Alpaca data client."""
    global _client
    if _client is not None:
        return _client

    api_key = settings.ALPACA_API_KEY
    secret_key = settings.ALPACA_SECRET_KEY

    if not api_key or not secret_key:
        logger.warning("Alpaca credentials missing — live prices unavailable")
        return None

    _client = StockHistoricalDataClient(api_key, secret_key)
    logger.info("Alpaca StockHistoricalDataClient initialized")
    return _client


def _fetch_alpaca_prices(tickers: list[str]) -> Dict[str, float]:
    """Fetch latest trade prices from Alpaca for US stocks/crypto."""
    if not tickers:
        return {}

    client = _get_alpaca_client()
    if not client:
        return {}

    try:
        request = StockLatestTradeRequest(symbol_or_symbols=tickers)
        trades = client.get_stock_latest_trade(request)
        prices = {}
        for symbol, trade in trades.items():
            if trade and trade.price:
                prices[symbol] = float(trade.price)
        return prices
    except Exception as e:
        logger.warning("Alpaca price fetch failed for %s: %s", tickers, e)
        return {}


def _fetch_yfinance_price(ticker: str) -> Optional[float]:
    """Fetch the latest price from yfinance for Indian market stocks."""
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if hist.empty:
            return None
        close = float(hist["Close"].iloc[-1])
        if math.isnan(close):
            return None
        return close
    except Exception as e:
        logger.warning("yfinance price fetch failed for %s: %s", ticker, e)
        return None


# ── Public API ──────────────────────────────────────────────────


def get_latest_price(ticker: str) -> Optional[float]:
    """Get the latest price for a single ticker.

    Routes to yfinance for Indian stocks, Alpaca for everything else.
    """
    if _is_indian_stock(ticker):
        return _fetch_yfinance_price(ticker)

    prices = _fetch_alpaca_prices([ticker])
    return prices.get(ticker)


def get_latest_prices(tickers: list[str]) -> Dict[str, float]:
    """Get the latest prices for multiple tickers in as few API calls as possible.

    Indian stocks (.NS/.BO) are fetched individually via yfinance.
    All other tickers are batched into a single Alpaca API call.
    Returns a dict of {ticker: price}. Missing tickers are omitted.
    """
    if not tickers:
        return {}

    prices: Dict[str, float] = {}

    # Separate Indian vs Alpaca tickers
    indian_tickers = [t for t in tickers if _is_indian_stock(t)]
    alpaca_tickers = [t for t in tickers if not _is_indian_stock(t)]

    # Batch fetch US/crypto from Alpaca
    if alpaca_tickers:
        alpaca_prices = _fetch_alpaca_prices(alpaca_tickers)
        prices.update(alpaca_prices)

    # Fetch Indian stocks individually from yfinance
    for ticker in indian_tickers:
        price = _fetch_yfinance_price(ticker)
        if price is not None:
            prices[ticker] = price

    return prices
