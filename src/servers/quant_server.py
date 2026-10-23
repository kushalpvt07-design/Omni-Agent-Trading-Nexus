import json
import os
import math
import logging
import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("omni-nexus.quant-server")

api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

mcp = FastMCP("QuantServer")


def _is_auth_error(exc: Exception) -> bool:
    """Detect HTTP 401/403 authentication failures from Alpaca SDK exceptions."""
    error_str = str(exc).lower()
    if any(code in error_str for code in ("401", "403", "unauthorized", "forbidden")):
        return True
    if hasattr(exc, "status_code") and getattr(exc, "status_code", None) in (401, 403):
        return True
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause is not None:
        cause_str = str(cause).lower()
        if any(code in cause_str for code in ("401", "403", "unauthorized", "forbidden")):
            return True
        if hasattr(cause, "response"):
            resp = getattr(cause, "response", None)
            if resp is not None and hasattr(resp, "status_code"):
                if resp.status_code in (401, 403):
                    return True
    return False


def compute_wilder_rsi(closes: pd.Series, period: int = 14) -> float:
    """Compute Wilder's smoothed Relative Strength Index (RSI) over the given period."""
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


@mcp.tool()
def get_daily_close_price(ticker: str, asset_class: str = "equity") -> str:
    ticker_upper = ticker.upper().strip()

    if not ticker_upper or len(ticker_upper) > 20:
        return json.dumps(
            {
                "status": "error",
                "error_code": "INVALID_TICKER",
                "message": "Invalid ticker symbol format. Must be 1-20 characters.",
            }
        )

    is_indian = ticker_upper.endswith(".NS") or ticker_upper.endswith(".BO")
    if is_indian:
        return _fetch_yfinance_quant(ticker_upper)

    if not api_key or not secret_key:
        logger.error("Alpaca API credentials are missing from environment variables.")
        return json.dumps(
            {
                "status": "error",
                "error_code": "AUTH_ERROR",
                "message": (
                    "Alpaca API credentials are not configured. "
                    "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env file."
                ),
            }
        )

    try:
        # 60 calendar days guarantees >= 30 trading days even across holiday weeks (BUG-011)
        start_date = datetime.now(timezone.utc) - timedelta(days=60)

        if asset_class == "crypto" or "/" in ticker_upper:
            alpaca_ticker = ticker_upper.replace("-", "/")
            client = CryptoHistoricalDataClient(api_key, secret_key)
            request_params = CryptoBarsRequest(
                symbol_or_symbols=[alpaca_ticker],
                timeframe=TimeFrame.Day,
                start=start_date,
            )
            bars = client.get_crypto_bars(request_params).df
        else:
            client = StockHistoricalDataClient(api_key, secret_key)
            request_params = StockBarsRequest(
                symbol_or_symbols=[ticker_upper],
                timeframe=TimeFrame.Day,
                start=start_date,
                adjustment=Adjustment.ALL,
            )
            bars = client.get_stock_bars(request_params).df

        if bars.empty:
            return json.dumps(
                {
                    "status": "error",
                    "error_code": "NO_DATA",
                    "message": f"No data found for ticker {ticker_upper}.",
                }
            )

        closes = bars["close"].tail(30)
        latest_close = float(closes.iloc[-1])
        sma = float(closes.mean())

        if len(closes) >= 2:
            prev_close = float(closes.iloc[-2])
            if prev_close > 0 and abs(latest_close - prev_close) / prev_close > 0.5:
                return json.dumps(
                    {
                        "status": "error",
                        "error_code": "DATA_CORRUPT",
                        "message": (
                            f"DATA_CORRUPT: {ticker_upper} moved more than 50% day-over-day "
                            f"({prev_close:.4f} → {latest_close:.4f}). Possible split or bad tick."
                        ),
                    }
                )

        annualization_factor = (
            math.sqrt(365) if (asset_class == "crypto" or "/" in ticker_upper) else math.sqrt(252)
        )
        log_returns = np.log(closes / closes.shift(1)).dropna()
        if len(log_returns) >= 2:
            daily_vol = float(log_returns.std(ddof=1))
            annualized_vol = daily_vol * annualization_factor
        else:
            daily_vol = 0.0
            annualized_vol = 0.0

        rsi_14 = compute_wilder_rsi(bars["close"], period=14)

        vols_30 = bars["volume"].tail(30).dropna()
        raw_vol = float(bars["volume"].iloc[-1])
        latest_volume = round(raw_vol) if not math.isnan(raw_vol) else 0
        avg_vol_30 = float(vols_30.mean()) if not vols_30.empty else 0.0
        volume_ratio_30d = round(latest_volume / avg_vol_30, 2) if avg_vol_30 > 0 else 1.0

        # Keep chronological order (oldest -> newest) so LLM reads trend direction accurately (BUG-010)
        history_data = []
        for idx, row in bars.tail(30).iterrows():
            ts = idx[1] if isinstance(idx, tuple) else idx
            date_str = pd.to_datetime(ts).strftime("%Y-%m-%d")

            close_val = row.get("close") if "close" in row else row.get("Close")
            vol_val = row.get("volume") if "volume" in row else row.get("Volume")
            vol_clean = (
                round(float(vol_val))
                if vol_val is not None and not math.isnan(float(vol_val))
                else 0
            )

            history_data.append(
                {
                    "date": date_str,
                    "close": round(float(close_val), 4),
                    "volume": vol_clean,
                }
            )

        payload = {
            "status": "success",
            "ticker": ticker_upper,
            "latest_close": latest_close,
            "latest_volume": latest_volume,
            "thirty_day_sma": round(sma, 4),
            "rsi_14": rsi_14,
            "volume_ratio_30d": volume_ratio_30d,
            "volatility_metrics": {
                "daily_log_return_std": daily_vol,
                "annualized_volatility": annualized_vol,
                "30_day_standard_deviation": daily_vol,
            },
            "thirty_day_trend": history_data,
        }

        return json.dumps(payload, indent=2)

    except Exception as e:
        if _is_auth_error(e):
            logger.error(
                "AUTH_ERROR for %s: Alpaca rejected credentials (HTTP 401/403).",
                ticker_upper,
            )
            return json.dumps(
                {
                    "status": "error",
                    "error_code": "AUTH_ERROR",
                    "message": (
                        f"Alpaca authentication failed for {ticker_upper} (HTTP 401/403). "
                        "Your API keys may be expired, revoked, or incorrectly configured."
                    ),
                }
            )

        logger.exception("Quant server error fetching data for %s", ticker_upper)
        return json.dumps(
            {
                "status": "error",
                "error_code": "DATA_FETCH_ERROR",
                "message": f"Failed to retrieve live data for {ticker_upper}: {str(e)}",
            }
        )


def _fetch_yfinance_quant(ticker_upper: str) -> str:
    """Fetch quant data for Indian market stocks via yfinance."""
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker_upper)
        hist = stock.history(period="60d")

        if hist.empty:
            return json.dumps(
                {
                    "status": "error",
                    "error_code": "NO_DATA",
                    "message": f"No data found for Indian ticker {ticker_upper} via yfinance.",
                }
            )

        closes = hist["Close"].dropna().tail(30)
        latest_close = float(closes.iloc[-1])
        sma = float(closes.mean())

        if len(closes) >= 2:
            prev_close = float(closes.iloc[-2])
            if prev_close > 0 and abs(latest_close - prev_close) / prev_close > 0.5:
                return json.dumps(
                    {
                        "status": "error",
                        "error_code": "DATA_CORRUPT",
                        "message": (
                            f"DATA_CORRUPT: {ticker_upper} moved >50% day-over-day "
                            f"({prev_close:.4f} → {latest_close:.4f})."
                        ),
                    }
                )

        log_returns = np.log(closes / closes.shift(1)).dropna()
        if len(log_returns) >= 2:
            daily_vol = float(log_returns.std(ddof=1))
            annualized_vol = daily_vol * math.sqrt(252)
        else:
            daily_vol = 0.0
            annualized_vol = 0.0

        rsi_14 = compute_wilder_rsi(hist["Close"].dropna(), period=14)

        vols_30 = hist["Volume"].tail(30).dropna()
        raw_vol = float(hist["Volume"].iloc[-1])
        latest_volume = round(raw_vol) if not math.isnan(raw_vol) else 0
        avg_vol_30 = float(vols_30.mean()) if not vols_30.empty else 0.0
        volume_ratio_30d = round(latest_volume / avg_vol_30, 2) if avg_vol_30 > 0 else 1.0

        # Keep chronological order (oldest -> newest)
        history_data = []
        for date, row in hist.tail(30).iterrows():
            close_val = float(row["Close"])
            vol_val = float(row["Volume"]) if not math.isnan(float(row["Volume"])) else 0
            history_data.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "close": round(close_val, 4),
                    "volume": round(vol_val),
                }
            )

        return json.dumps(
            {
                "status": "success",
                "ticker": ticker_upper,
                "latest_close": latest_close,
                "latest_volume": latest_volume,
                "thirty_day_sma": round(sma, 4),
                "rsi_14": rsi_14,
                "volume_ratio_30d": volume_ratio_30d,
                "volatility_metrics": {
                    "daily_log_return_std": daily_vol,
                    "annualized_volatility": annualized_vol,
                    "30_day_standard_deviation": daily_vol,
                },
                "thirty_day_trend": history_data,
            },
            indent=2,
        )
    except Exception as e:
        logger.exception("yfinance quant fetch failed for %s", ticker_upper)
        return json.dumps(
            {
                "status": "error",
                "error_code": "DATA_FETCH_ERROR",
                "message": f"Failed to retrieve yfinance data for {ticker_upper}: {str(e)}",
            }
        )


if __name__ == "__main__":
    mcp.run()
