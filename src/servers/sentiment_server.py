import json
import logging
import yfinance as yf
import requests
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("omni-nexus.sentiment-server")

mcp = FastMCP("SentimentServer")


@mcp.tool()
def analyze_market_sentiment(ticker: str, asset_class: str = "equity") -> str:
    """Fetches real market news using yfinance for sentiment analysis."""
    ticker_upper = "".join(
        e for e in ticker.upper() if e.isalnum() or e in ["-", "/"]
    )
    clean_ticker = ticker_upper.replace("/", "-")

    # Enforce Yahoo Finance format for crypto assets
    if asset_class == "crypto" or "-" in ticker_upper:
        yf_ticker = (
            clean_ticker if "-USD" in clean_ticker else f"{clean_ticker}-USD"
        )
    else:
        yf_ticker = clean_ticker

    try:
        with requests.Session() as clean_session:
            clean_session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )
            stock = yf.Ticker(yf_ticker, session=clean_session)
            news = stock.news

        headlines = []
        if news:
            for item in news[:2]:
                content = item.get("content", {})
                title = content.get("title") or item.get("title", "")
                summary = content.get("summary") or item.get("summary", "")
                if title:
                    headlines.append(f"Title: {title} | Summary: {summary}")
        else:
            headlines.append(f"No recent news found for {yf_ticker}.")

        payload = {
            "status": "success",
            "ticker": yf_ticker,
            "top_headlines": headlines,
        }

        return json.dumps(payload, indent=2)
    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "message": f"Failed to retrieve news: {str(e)}",
            }
        )


if __name__ == "__main__":
    mcp.run()
