import json
import os
import math
import logging
import pandas as pd
from mcp.server.fastmcp import FastMCP
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("omni-nexus.quant-server")

api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

mcp = FastMCP("QuantServer")


def _is_auth_error(exc: Exception) -> bool:
    """Detect HTTP 401/403 authentication failures from Alpaca SDK exceptions.

    The Alpaca SDK wraps HTTP errors in various exception types across versions.
    This helper inspects the exception chain to reliably detect auth failures
    regardless of SDK version.
    """
    error_str = str(exc).lower()

    # Direct status-code mentions in the exception message
    if any(code in error_str for code in ("401", "403", "unauthorized", "forbidden")):
        return True

    # Alpaca SDK may expose the HTTP status via a `status_code` attribute
    if hasattr(exc, "status_code") and getattr(exc, "status_code", None) in (401, 403):
        return True

    # Walk the exception chain (e.g. HTTPError wrapped inside an SDK error)
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

    # ── Fast-fail: validate credentials before making any API call ───
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
        # Alpaca requires timezone-aware datetime objects
        start_date = datetime.now(timezone.utc) - timedelta(days=45)

        if asset_class == "crypto":
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
        std_dev = float(closes.std()) if len(closes) > 1 else 0.0
        sma = float(closes.mean())
        latest_close = float(closes.iloc[-1])
        raw_vol = bars["volume"].iloc[-1]
        latest_volume = int(raw_vol) if not math.isnan(raw_vol) else 0

        # Data integrity check — reject if price deviates > 50% from SMA
        if sma > 0 and abs(latest_close - sma) / sma > 0.5:
            return json.dumps(
                {
                    "status": "error",
                    "error_code": "DATA_CORRUPT",
                    "message": f"DATA_CORRUPT: Live price ({latest_close}) deviates from 30-day SMA ({sma}) by > 50%. Possible proxy mismatch or split anomaly.",
                }
            )

        history_data = []
        for idx, row in bars.tail(5).iterrows():
            ts = idx[1] if isinstance(idx, tuple) else idx
            date_str = pd.to_datetime(ts).strftime("%Y-%m-%d")

            close_val = row.get("close") if "close" in row else row.get("Close")
            vol_val = row.get("volume") if "volume" in row else row.get("Volume")
            vol_clean = (
                int(vol_val)
                if vol_val is not None and not math.isnan(float(vol_val))
                else 0
            )

            history_data.append(
                {
                    "date": date_str,
                    "close": round(float(close_val), 2),
                    "volume": vol_clean,
                }
            )

        history_data.reverse()

        payload = {
            "status": "success",
            "ticker": ticker_upper,
            "latest_close": latest_close,
            "latest_volume": latest_volume,
            "volatility_metrics": {
                "30_day_standard_deviation": round(std_dev, 2),
            },
            "thirty_day_trend": history_data,
        }

        return json.dumps(payload, indent=2)

    except Exception as e:
        # ── Classify the failure for upstream agents ──────────────────
        if _is_auth_error(e):
            logger.error(
                "AUTH_ERROR for %s: Alpaca rejected credentials (HTTP 401/403). "
                "Regenerate your API keys at https://app.alpaca.markets/",
                ticker_upper,
            )
            return json.dumps(
                {
                    "status": "error",
                    "error_code": "AUTH_ERROR",
                    "message": (
                        f"Alpaca authentication failed for {ticker_upper} (HTTP 401/403). "
                        "Your API keys may be expired, revoked, or incorrectly configured. "
                        "Regenerate them at https://app.alpaca.markets/ and update your .env file."
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


if __name__ == "__main__":
    mcp.run()

