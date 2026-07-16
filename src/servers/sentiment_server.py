import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SentimentServer")

@mcp.tool()
def analyze_market_sentiment(ticker: str) -> str:
    """Mocking a perfect bullish news day to test the execution pipeline."""
    ticker_upper = ''.join(e for e in ticker.upper() if e.isalnum())
    
    payload = {
        "status": "success",
        "ticker": ticker_upper,
        "sentiment_label": "BULLISH",
        "latest_headlines": [
            f"{ticker_upper} shatters quarterly earnings expectations!",
            f"Analysts upgrade {ticker_upper} to strong buy following new AI product launch.",
            f"Record profits drive {ticker_upper} stock to all-time highs."
        ]
    }
    
    return json.dumps(payload, indent=2)

if __name__ == "__main__":
    mcp.run()
