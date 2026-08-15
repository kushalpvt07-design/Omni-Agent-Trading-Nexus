import yfinance as yf
import math
import logging

logger = logging.getLogger("omni-nexus.utils")


def _build_chart_data(hist, time_format="%d/%m"):
    """Convert a DataFrame of historical prices into chart-ready JSON data."""
    chart_data = []
    for date, row in hist.iterrows():
        val = float(row["Close"])
        chart_data.append(
            {
                "time": date.strftime(time_format),
                "price": round(val, 2) if not math.isnan(val) else 0.0,
            }
        )
    return chart_data


def get_live_asset_data(ticker_symbol: str):
    """Fetches live price, change %, volatility, and chart data for a ticker.

    Returns chart data for multiple timeframes (1D, 5D, 15D, 1M, ALL) so the
    frontend can switch between them without an extra API round-trip.

    This is a synchronous function — callers in async contexts should wrap it
    with ``asyncio.to_thread()`` to avoid blocking the event loop.
    """
    if not ticker_symbol or ticker_symbol == "UNKNOWN":
        return None

    ticker_upper = ticker_symbol.upper().strip()

    # Preserve Indian market exchange suffixes (.NS for NSE, .BO for BSE)
    is_indian_market = ticker_upper.endswith(".NS") or ticker_upper.endswith(".BO")

    if is_indian_market:
        clean_ticker = ticker_upper  # Keep as-is for Yahoo Finance
    else:
        clean_ticker = ticker_upper.replace("/", "-")

    # Determine currency based on market
    currency = "INR" if is_indian_market else "USD"

    try:
        ticker = yf.Ticker(clean_ticker)
        hist = ticker.history(period="1mo")

        # Smart fallback for crypto: if empty, try adding the -USD suffix
        # (skip for Indian market tickers which already have their exchange suffix)
        if hist.empty and not is_indian_market and "-" not in clean_ticker:
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

        # Build chart data for the default 1M period
        chart_data = _build_chart_data(hist)

        # Build chart data for all supported timeframes
        timeframe_data = {
            "1M": chart_data,  # Already have this from the main query
        }

        # 1D: Fetch intraday hourly data for detailed 1-day view
        try:
            hist_1d = ticker.history(period="1d", interval="1h")
            if not hist_1d.empty:
                timeframe_data["1D"] = _build_chart_data(hist_1d, time_format="%H:%M")
            else:
                # Fallback: use last day from daily data
                timeframe_data["1D"] = _build_chart_data(hist.iloc[-1:])
        except Exception:
            timeframe_data["1D"] = _build_chart_data(hist.iloc[-1:])

        # 5D and 15D: Slice from existing monthly data
        if len(hist) >= 5:
            timeframe_data["5D"] = _build_chart_data(hist.iloc[-5:])
        else:
            timeframe_data["5D"] = chart_data
        if len(hist) >= 15:
            timeframe_data["15D"] = _build_chart_data(hist.iloc[-15:])
        else:
            timeframe_data["15D"] = chart_data

        # ALL: Fetch extended 1-year history
        try:
            hist_all = ticker.history(period="1y")
            if not hist_all.empty:
                timeframe_data["ALL"] = _build_chart_data(hist_all)
            else:
                timeframe_data["ALL"] = chart_data
        except Exception:
            timeframe_data["ALL"] = chart_data

        return {
            "ticker": clean_ticker,
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "volatility": round(volatility, 2),
            "is_positive": change_pct >= 0,
            "chart_data": chart_data,
            "timeframe_data": timeframe_data,
            "currency": currency,
        }
    except Exception as e:
        logger.warning("Error fetching asset data for %s: %s", ticker_symbol, e)
        return None
