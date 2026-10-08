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

from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest, CryptoLatestTradeRequest

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


def _is_crypto(ticker: str) -> bool:
    """Crypto tickers use Alpaca's slash format, e.g. BTC/USD."""
    return "/" in ticker


def _fetch_crypto_prices(tickers: list[str]) -> Dict[str, float]:
    """Fetch latest trade prices from Alpaca for crypto assets.

    §5.1 — Crypto symbols are invalid in StockLatestTradeRequest; they must
    go through CryptoHistoricalDataClient / CryptoLatestTradeRequest.
    """
    if not tickers:
        return {}

    api_key = settings.ALPACA_API_KEY
    secret_key = settings.ALPACA_SECRET_KEY
    if not api_key or not secret_key:
        return {}

    try:
        client = CryptoHistoricalDataClient(api_key, secret_key)
        request = CryptoLatestTradeRequest(symbol_or_symbols=tickers)
        trades = client.get_crypto_latest_trade(request)
        prices = {}
        for symbol, trade in trades.items():
            if trade and trade.price:
                prices[symbol] = float(trade.price)
        return prices
    except Exception as e:
        logger.warning("Alpaca crypto price fetch failed for %s: %s", tickers, e)
        return {}


def get_latest_price(ticker: str) -> Optional[float]:
    """Get the latest price for a single ticker.

    Routes to yfinance for Indian stocks, Alpaca crypto client for crypto,
    and Alpaca stock client for everything else.
    """
    if _is_indian_stock(ticker):
        return _fetch_yfinance_price(ticker)

    if _is_crypto(ticker):
        prices = _fetch_crypto_prices([ticker])
        return prices.get(ticker)

    prices = _fetch_alpaca_prices([ticker])
    return prices.get(ticker)


def get_latest_prices(tickers: list[str]) -> Dict[str, float]:
    """Get the latest prices for multiple tickers in as few API calls as possible.

    Indian stocks (.NS/.BO) are fetched individually via yfinance.
    Crypto tickers (containing /) are batched into a CryptoLatestTradeRequest.
    All other tickers are batched into a single StockLatestTradeRequest.
    Returns a dict of {ticker: price}. Missing tickers are omitted.

    §5.1 — Previously crypto symbols in a stock batch caused the entire
    response to fail, silently zeroing all US stock prices.
    """
    if not tickers:
        return {}

    prices: Dict[str, float] = {}

    # Partition tickers by routing destination
    indian_tickers = [t for t in tickers if _is_indian_stock(t)]
    crypto_tickers = [t for t in tickers if not _is_indian_stock(t) and _is_crypto(t)]
    stock_tickers  = [t for t in tickers if not _is_indian_stock(t) and not _is_crypto(t)]

    # Batch fetch US stocks from Alpaca
    if stock_tickers:
        alpaca_prices = _fetch_alpaca_prices(stock_tickers)
        prices.update(alpaca_prices)

    # Batch fetch crypto from Alpaca (separate client)
    if crypto_tickers:
        crypto_prices = _fetch_crypto_prices(crypto_tickers)
        prices.update(crypto_prices)

    # Fetch Indian stocks individually from yfinance
    for ticker in indian_tickers:
        price = _fetch_yfinance_price(ticker)
        if price is not None:
            prices[ticker] = price

    return prices
