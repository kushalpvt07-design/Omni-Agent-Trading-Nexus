import json
import yfinance as yf
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP named "QuantServer"
mcp = FastMCP("QuantServer")

@mcp.tool()
def get_daily_close_price(ticker: str) -> str:
    """
    Fetches the actual live/latest daily closing price, volume, and 5-day historical trend 
    for a given equity ticker symbol from Yahoo Finance.
    """
    ticker_upper = ticker.upper().strip()
    # Strip out any punctuation the LLM might have accidentally included
    ticker_upper = ''.join(e for e in ticker_upper if e.isalnum())
    
    if not ticker_upper or len(ticker_upper) > 5:
        return json.dumps({"status": "error", "message": "Invalid ticker symbol format."})
    
    try:
        # Fetch live data from Yahoo Finance
        stock = yf.Ticker(ticker_upper)
        hist = stock.history(period="1mo")
        
        if hist.empty:
            return json.dumps({"status": "error", "message": f"No data found for ticker {ticker_upper}. It might be delisted or invalid."})

        # Calculate 30-day volatility (Standard Deviation of Close)
        std_dev = float(hist['Close'].std())

        # Format the 30-day trend
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })
            
        # Sort so the newest date is first
        history_data.reverse()
        latest = history_data[0]
        
        payload = {
            "status": "success",
            "ticker": ticker_upper,
            "latest_close": latest["close"],
            "latest_volume": latest["volume"],
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
