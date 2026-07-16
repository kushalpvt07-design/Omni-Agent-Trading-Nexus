import json
import random
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP named "QuantServer"
mcp = FastMCP("QuantServer")

def generate_mock_history(ticker: str, days: int = 5) -> list:
    """Helper to generate consistent financial mock data for testing."""
    random.seed(ticker)  # Ensures the same ticker gives stable mock results
    base_price = {"AAPL": 175.0, "MSFT": 420.0, "GOOGL": 150.0, "NVDA": 850.0}.get(ticker, 100.0)
    
    history = []
    current_date = datetime.now()
    
    for i in range(days):
        date_str = (current_date - timedelta(days=i)).strftime("%Y-%m-%d")
        change = random.uniform(-0.03, 0.03)
        close_price = round(base_price * (1 + change), 2)
        volume = random.randint(1000000, 5000000)
        
        history.append({
            "date": date_str,
            "close": close_price,
            "volume": volume
        })
    return history

@mcp.tool()
def get_daily_close_price(ticker: str) -> str:
    """
    Fetches the latest daily closing price, volume, and 5-day historical trend 
    for a given equity ticker symbol.
    """
    ticker_upper = ticker.upper().strip()
    
    # Contextual check to make sure the agent sent a clean ticker
    if not ticker_upper or len(ticker_upper) > 5:
        return json.dumps({"status": "error", "message": "Invalid ticker symbol format."})
    
    # -----------------------------------------------------------------
    # PRODUCTION NOTE: To connect a real financial API later, you would replace
    # this block with an actual API call, e.g.:
    # data = requests.get(f"https://api.provider.com/quote?symbol={ticker_upper}").json()
    # -----------------------------------------------------------------
    
    try:
        history = generate_mock_history(ticker_upper, days=5)
        latest = history[0]
        
        payload = {
            "status": "success",
            "ticker": ticker_upper,
            "timestamp": datetime.now().isoformat(),
            "latest_close": latest["close"],
            "latest_volume": latest["volume"],
            "five_day_trend": history
        }
        
        return json.dumps(payload, indent=2)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to retrieve data: {str(e)}"})

if __name__ == "__main__":
    # Launch the MCP server via the standard stdio transport layer
    mcp.run()
