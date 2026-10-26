import math
import logging
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("omni-nexus.utils")


def _compute_wilder_rsi(closes: pd.Series, period: int = 14) -> float:
    clean = closes.dropna()
    if len(clean) < period + 1:
        return 50.0
    delta = clean.diff().dropna()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().iloc[-1]
    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(float(rsi), 2) if not math.isnan(rsi) else 50.0


def _build_chart_data(hist: pd.DataFrame, time_format="%d/%m", sma_series: pd.Series | None = None):
    """Convert a DataFrame of historical prices into chart-ready JSON data with OHLC + SMA."""
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
        sma_val = None
        if sma_series is not None and date in sma_series.index:
            raw_sma = float(sma_series.loc[date])
            if not math.isnan(raw_sma):
                sma_val = round(raw_sma, 2)

        chart_data.append(
            {
                "time": date.strftime(time_format),
                "price": round(close_val, 2),
                "open": round(open_val, 2),
                "high": round(high_val, 2),
                "low": round(low_val, 2),
                "close": round(close_val, 2),
                "ohlc_range": [round(low_val, 2), round(high_val, 2)],
                "sma": sma_val if sma_val is not None else round(close_val, 2),
            }
        )
    return chart_data


def get_live_asset_data(ticker_symbol: str):
    """Fetches live price, change %, 30-day log-return volatility, RSI-14, SMA-30, volume ratio, and chart data."""
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

        rolling_sma_30 = hist_60["Close"].rolling(window=30, min_periods=5).mean()
        hist = hist_60.tail(22)

        current_price = float(hist["Close"].iloc[-1])
        prev_price = float(hist["Close"].iloc[0])

        if math.isnan(current_price) or math.isnan(prev_price) or prev_price == 0:
            return None

        change_pct = ((current_price - prev_price) / prev_price) * 100
        if math.isnan(change_pct):
            change_pct = 0.0

        closes_30 = hist_60["Close"].tail(30)
        sma_30_latest = float(closes_30.mean()) if not closes_30.empty else current_price
        rsi_14 = _compute_wilder_rsi(hist_60["Close"], period=14)

        vols_30 = hist_60["Volume"].tail(30).dropna() if "Volume" in hist_60 else pd.Series(dtype=float)
        latest_vol = float(vols_30.iloc[-1]) if not vols_30.empty else 0.0
        avg_vol_30 = float(vols_30.mean()) if not vols_30.empty else 0.0
        volume_ratio_30d = round(latest_vol / avg_vol_30, 2) if avg_vol_30 > 0 else 1.0

        log_returns = np.log(closes_30 / closes_30.shift(1)).dropna()
        annualization_days = 365 if (not is_indian_market and "-" in clean_ticker) else 252
        volatility = (
            float(log_returns.std(ddof=1) * math.sqrt(annualization_days) * 100.0)
            if len(log_returns) >= 2
            else 0.0
        )
        if math.isnan(volatility):
            volatility = 0.0

        chart_data = _build_chart_data(hist, sma_series=rolling_sma_30)
        timeframe_data = {
            "1M": chart_data,
        }

        try:
            hist_1d = ticker.history(period="1d", interval="1h")
            if not hist_1d.empty:
                sma_1d = hist_1d["Close"].rolling(window=6, min_periods=1).mean()
                timeframe_data["1D"] = _build_chart_data(hist_1d, time_format="%H:%M", sma_series=sma_1d)
            else:
                timeframe_data["1D"] = _build_chart_data(hist.iloc[-1:], sma_series=rolling_sma_30)
        except Exception:
            timeframe_data["1D"] = _build_chart_data(hist.iloc[-1:], sma_series=rolling_sma_30)

        if len(hist) >= 5:
            timeframe_data["5D"] = _build_chart_data(hist.iloc[-5:], sma_series=rolling_sma_30)
        else:
            timeframe_data["5D"] = chart_data

        if len(hist) >= 15:
            timeframe_data["15D"] = _build_chart_data(hist.iloc[-15:], sma_series=rolling_sma_30)
        else:
            timeframe_data["15D"] = chart_data

        try:
            hist_all = ticker.history(period="1y")
            if not hist_all.empty:
                sma_all = hist_all["Close"].rolling(window=30, min_periods=5).mean()
                timeframe_data["ALL"] = _build_chart_data(hist_all, sma_series=sma_all)
            else:
                timeframe_data["ALL"] = chart_data
        except Exception:
            timeframe_data["ALL"] = chart_data

        return {
            "ticker": clean_ticker,
            "current_price": round(current_price, 2),
            "thirty_day_sma": round(sma_30_latest, 2),
            "rsi_14": rsi_14,
            "volume_ratio_30d": volume_ratio_30d,
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
