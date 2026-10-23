import math
import logging
import numpy as np
import yfinance as yf

logger = logging.getLogger("omni-nexus.utils")


def _build_chart_data(hist, time_format="%d/%m"):
    """Convert a DataFrame of historical prices into chart-ready JSON data."""
    chart_data = []
    for date, row in hist.iterrows():
        close_val = float(row["Close"])
        if math.isnan(close_val):
            continue
        open_val = (
            float(row["Open"])
            if "Open" in row and not math.isnan(float(row["Open"]))
            else close_val
        )
        high_val = (
            float(row["High"])
            if "High" in row and not math.isnan(float(row["High"]))
            else close_val
        )
        low_val = (
            float(row["Low"])
            if "Low" in row and not math.isnan(float(row["Low"]))
            else close_val
        )
        chart_data.append(
            {
                "time": date.strftime(time_format),
                "price": round(close_val, 2),
                "open": round(open_val, 2),
                "high": round(high_val, 2),
                "low": round(low_val, 2),
                "close": round(close_val, 2),
            }
        )
    return chart_data


def get_live_asset_data(ticker_symbol: str):
    """Fetches live price, change %, 30-trading-day log-return volatility, and chart data."""
    if not ticker_symbol or ticker_symbol == "UNKNOWN":
        return None

    ticker_upper = ticker_symbol.upper().strip()
    is_indian_market = ticker_upper.endswith(".NS") or ticker_upper.endswith(".BO")

    if is_indian_market:
        clean_ticker = ticker_upper
    else:
        clean_ticker = ticker_upper.replace("/", "-")

    currency = "INR" if is_indian_market else "USD"

    try:
        ticker = yf.Ticker(clean_ticker)
        # Fetch 60 calendar days so 30 trading days are available for volatility (BUG-011)
        hist_60 = ticker.history(period="60d")

        if (
            hist_60.empty
            and not is_indian_market
            and "-" not in clean_ticker
            and "." not in clean_ticker
            and len(clean_ticker) <= 5
            and clean_ticker.isalpha()
        ):
            crypto_ticker = f"{clean_ticker}-USD"
            ticker = yf.Ticker(crypto_ticker)
            hist_60 = ticker.history(period="60d")
            clean_ticker = crypto_ticker

        if hist_60.empty:
            return None

        hist_60 = hist_60.dropna(subset=["Close"])
        if hist_60.empty:
            return None

        # Use last ~22 trading bars (~1 month) for 1M chart display
        hist = hist_60.tail(22)
        current_price = float(hist["Close"].iloc[-1])
        prev_price = float(hist["Close"].iloc[0])

        if math.isnan(current_price) or math.isnan(prev_price) or prev_price == 0:
            return None

        change_pct = ((current_price - prev_price) / prev_price) * 100
        if math.isnan(change_pct):
            change_pct = 0.0

        # Standardized 30-trading-day log-return annualized volatility matching quant_server.py (BUG-011)
        closes_30 = hist_60["Close"].tail(30)
        log_returns = np.log(closes_30 / closes_30.shift(1)).dropna()
        annualization_days = 365 if (not is_indian_market and "-" in clean_ticker) else 252
        volatility = (
            float(log_returns.std(ddof=1) * math.sqrt(annualization_days) * 100.0)
            if len(log_returns) >= 2
            else 0.0
        )

        if math.isnan(volatility):
            volatility = 0.0

        chart_data = _build_chart_data(hist)
        timeframe_data = {
            "1M": chart_data,
        }

        try:
            hist_1d = ticker.history(period="1d", interval="1h")
            if not hist_1d.empty:
                timeframe_data["1D"] = _build_chart_data(hist_1d, time_format="%H:%M")
            else:
                timeframe_data["1D"] = _build_chart_data(hist.iloc[-1:])
        except Exception:
            timeframe_data["1D"] = _build_chart_data(hist.iloc[-1:])

        if len(hist) >= 5:
            timeframe_data["5D"] = _build_chart_data(hist.iloc[-5:])
        else:
            timeframe_data["5D"] = chart_data

        if len(hist) >= 15:
            timeframe_data["15D"] = _build_chart_data(hist.iloc[-15:])
        else:
            timeframe_data["15D"] = chart_data

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
