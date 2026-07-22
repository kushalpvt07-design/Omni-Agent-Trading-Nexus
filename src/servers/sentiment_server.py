import json
import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SentimentServer")

@mcp.tool()
def analyze_market_sentiment(ticker: str) -> str:
    """Fetches real market news using yfinance for sentiment analysis."""
    ticker_upper = ''.join(e for e in ticker.upper() if e.isalnum())
    
    # Map cryptocurrencies to Yahoo Finance's format
    crypto_assets = {"BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "DOT", "LINK"}
    yf_ticker = f"{ticker_upper}-USD" if ticker_upper in crypto_assets else ticker_upper
    
    try:
        stock = yf.Ticker(yf_ticker)
        news = stock.news
        
        headlines = []
        if news:
            for item in news[:5]:
                content = item.get("content", {})
                title = content.get("title") or item.get("title", "")
                summary = content.get("summary") or item.get("summary", "")
                if title:
                    headlines.append(f"Title: {title} | Summary: {summary}")
        else:
            headlines.append(f"No recent news found for {ticker_upper}.")
            
        payload = {
            "status": "success",
            "ticker": ticker_upper,
            "latest_headlines": headlines
        }
        
        return json.dumps(payload, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to retrieve news: {str(e)}"})

if __name__ == "__main__":
    mcp.run()
