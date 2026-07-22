import json
import os
import math
from mcp.server.fastmcp import FastMCP
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("ALPACA_API_KEY")
secret_key = os.environ.get("ALPACA_SECRET_KEY")

mcp = FastMCP("QuantServer")

@mcp.tool()
def get_daily_close_price(ticker: str, asset_class: str = "equity") -> str:
    ticker_upper = ticker.upper().strip()
    
    if not ticker_upper or len(ticker_upper) > 10:
        return json.dumps({"status": "error", "message": "Invalid ticker symbol format."})
    
    try:
        start_date = datetime.now() - timedelta(days=45) # Fetch enough data for 30 trading days
        
        if asset_class == "crypto":
            client = CryptoHistoricalDataClient(api_key, secret_key)
            request_params = CryptoBarsRequest(
                symbol_or_symbols=[ticker_upper],
                timeframe=TimeFrame.Day,
                start=start_date
            )
            bars = client.get_crypto_bars(request_params).df
        else:
            client = StockHistoricalDataClient(api_key, secret_key)
            request_params = StockBarsRequest(
                symbol_or_symbols=[ticker_upper],
                timeframe=TimeFrame.Day,
                start=start_date
            )
            bars = client.get_stock_bars(request_params).df
            
        if bars.empty:
            return json.dumps({"status": "error", "message": f"No data found for ticker {ticker_upper}."})

        # Calculate 30-day volatility and SMA
        closes = bars['close'].tail(30)
        std_dev = float(closes.std()) if len(closes) > 1 else 0.0
        sma = float(closes.mean())
        latest_close = float(closes.iloc[-1])
        latest_volume = int(bars['volume'].iloc[-1])
        
        # Mathematical Sanity Check (Data Validation Layer)
        if sma > 0 and abs(latest_close - sma) / sma > 0.5:
            return json.dumps({
                "status": "error", 
                "message": f"DATA_CORRUPT: Live price ({latest_close}) deviates from 30-day SMA ({sma}) by > 50%. Possible proxy mismatch or split anomaly."
            })

        history_data = []
        for idx, row in bars.tail(30).iterrows():
            history_data.append({
                "date": idx[1].strftime("%Y-%m-%d"),
                "close": round(row["close"], 2),
                "volume": int(row["volume"])
            })
            
        history_data.reverse()
        
        payload = {
            "status": "success",
            "ticker": ticker_upper,
            "latest_close": latest_close,
            "latest_volume": latest_volume,
            "volatility_metrics": {
                "30_day_standard_deviation": round(std_dev, 2)
            },
            "thirty_day_trend": history_data
        }
        
        return json.dumps(payload, indent=2)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to retrieve live data: {str(e)}"})

if __name__ == "__main__":
    mcp.run()
