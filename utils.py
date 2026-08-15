import yfinance as yf
import math
import logging

logger = logging.getLogger("omni-nexus.utils")


def get_live_asset_data(ticker_symbol: str):
    """Fetches live price, change %, volatility, and chart data for a ticker.

    This is a synchronous function — callers in async contexts should wrap it
    with ``asyncio.to_thread()`` to avoid blocking the event loop.
    """
    if not ticker_symbol or ticker_symbol == "UNKNOWN":
        return None

    ticker_upper = ticker_symbol.upper().strip()
    clean_ticker = ticker_upper.replace("/", "-")

    try:
        ticker = yf.Ticker(clean_ticker)
        hist = ticker.history(period="1mo")

        # Smart fallback for crypto: if empty, try adding the -USD suffix
        if hist.empty and "-" not in clean_ticker:
            crypto_ticker = f"{clean_ticker}-USD"
            ticker = yf.Ticker(crypto_ticker)
            hist = ticker.history(period="1mo")
            clean_ticker = crypto_ticker

        if hist.empty:
            return None

        current_price = float(hist["Close"].iloc[-1])
        prev_price = float(hist["Close"].iloc[0])

        # JSON serialization safety — prevent ZeroDivisionError and NaN payloads
        if math.isnan(current_price) or math.isnan(prev_price) or prev_price == 0:
            return None

        change_pct = ((current_price - prev_price) / prev_price) * 100
        if math.isnan(change_pct):
            change_pct = 0.0

        returns = hist["Close"].pct_change().dropna()
        volatility = (
            float(returns.std() * (252**0.5) * 100) if not returns.empty else 0.0
        )

        if math.isnan(volatility):
            volatility = 0.0

        chart_data = []
        for date, row in hist.iterrows():
            val = float(row["Close"])
            chart_data.append(
                {
                    "time": date.strftime("%b %d"),
                    "price": round(val, 2) if not math.isnan(val) else 0.0,
                }
            )

        return {
            "ticker": clean_ticker,
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "volatility": round(volatility, 2),
            "is_positive": change_pct >= 0,
            "chart_data": chart_data,
        }
    except Exception as e:
        logger.warning("Error fetching asset data for %s: %s", ticker_symbol, e)
        return None
