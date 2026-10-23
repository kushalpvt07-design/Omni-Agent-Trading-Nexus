import os
import json
import logging
import yfinance as yf
import requests
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("omni-nexus.sentiment-server")

mcp = FastMCP("SentimentServer")

BULLISH_KEYWORDS = {
    "surge", "surges", "surging", "rally", "rallies", "rallying",
    "gain", "gains", "gained", "rise", "rises", "rising", "soar",
    "soars", "soaring", "jump", "jumps", "jumped", "boost", "boosts",
    "bullish", "upgrade", "upgrades", "upgraded", "beat", "beats",
    "outperform", "record", "high", "breakout", "growth", "profit",
    "strong", "buy", "positive", "optimistic", "recover", "recovery",
    "upbeat", "momentum", "opportunity", "rebound", "advance",
}

BEARISH_KEYWORDS = {
    "drop", "drops", "dropped", "fall", "falls", "falling", "decline",
    "declines", "declining", "crash", "crashes", "crashing", "plunge",
    "plunges", "plunging", "loss", "losses", "sink", "sinks", "sinking",
    "bearish", "downgrade", "downgrades", "downgraded", "miss", "misses",
    "underperform", "low", "sell", "selloff", "sell-off", "negative",
    "pessimistic", "risk", "warning", "fear", "weak", "slump", "tumble",
    "concern", "concerns", "worried", "recession", "layoff", "layoffs",
    "cut", "cuts", "deficit", "debt", "fraud", "scandal", "lawsuit",
    "fail", "fails", "failed",
}

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "without", "hardly", "barely",
    "fails", "failed", "fail", "lack", "lacks",
}


def _compute_sentiment(headlines: list[str]) -> tuple[float, str]:
    """Compute a sentiment score (0-1) and label from headline text with negation handling."""
    if not headlines:
        return 0.5, "NEUTRAL"

    combined_text = " ".join(headlines).lower()
    raw_tokens = [w.strip(".,!?;:\"'()[]{}") for w in combined_text.split()]
    tokens = [t for t in raw_tokens if t]

    bullish_count = 0
    bearish_count = 0

    for idx, word in enumerate(tokens):
        window_start = max(0, idx - 2)
        preceding = tokens[window_start:idx]
        is_negated = any(p in NEGATION_WORDS for p in preceding)

        if word in BULLISH_KEYWORDS:
            if is_negated:
                bearish_count += 1
            else:
                bullish_count += 1
        elif word in BEARISH_KEYWORDS:
            if is_negated and word not in {"fail", "fails", "failed"}:
                bullish_count += 1
            else:
                bearish_count += 1

    total_signals = bullish_count + bearish_count
    if total_signals == 0:
        return 0.5, "NEUTRAL"

    raw_score = bullish_count / total_signals
    confidence = min(total_signals / 8.0, 1.0)
    score = 0.5 + (raw_score - 0.5) * confidence
    score = max(0.05, min(0.95, score))

    if score > 0.6:
        label = "BULLISH"
    elif score < 0.4:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    return round(score, 3), label


@mcp.tool()
def analyze_market_sentiment(ticker: str, asset_class: str = "equity") -> str:
    """Fetches real market news using Alpaca News API or yfinance for sentiment analysis."""
    ticker_upper = "".join(
        e for e in ticker.upper() if e.isalnum() or e in ["-", "/", "."]
    )

    is_indian_market = ticker_upper.endswith(".NS") or ticker_upper.endswith(".BO")

    if is_indian_market:
        yf_ticker = ticker_upper
    else:
        clean_ticker = ticker_upper.replace("/", "-")
        if asset_class == "crypto" or "-" in ticker_upper or "/" in ticker_upper:
            yf_ticker = (
                clean_ticker if "-USD" in clean_ticker else f"{clean_ticker}-USD"
            )
        else:
            yf_ticker = clean_ticker

    try:
        headlines: list[str] = []
        if is_indian_market:
            with requests.Session() as clean_session:
                clean_session.headers.update(
                    {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"
                        )
                    }
                )
                # Preserve .NS / .BO suffix first so Yahoo Finance queries the Indian listing (BUG-009)
                stock = yf.Ticker(yf_ticker, session=clean_session)
                news = stock.news
                if not news:
                    base_ticker = yf_ticker.rsplit(".", 1)[0]
                    stock = yf.Ticker(base_ticker, session=clean_session)
                    news = stock.news
                if news:
                    for item in news[:5]:
                        content = item.get("content", {}) if isinstance(item, dict) else {}
                        title = content.get("title") or (item.get("title", "") if isinstance(item, dict) else "")
                        summary = content.get("summary") or (item.get("summary", "") if isinstance(item, dict) else "")
                        if title:
                            headlines.append(f"Title: {title} | Summary: {summary}")
        else:
            from alpaca.data.historical import NewsClient
            from alpaca.data.requests import NewsRequest

            api_key = os.environ.get("ALPACA_API_KEY")
            secret_key = os.environ.get("ALPACA_SECRET_KEY")

            if api_key and secret_key:
                client = NewsClient(api_key, secret_key)
                req = NewsRequest(symbols=ticker_upper.replace("-", "/"), limit=5)
                news_items = client.get_news(req)

                items_list = []
                if hasattr(news_items, "news"):
                    items_list = news_items.news
                elif hasattr(news_items, "dict"):
                    items_list = news_items.dict().get("news", [])

                for item in items_list:
                    if isinstance(item, dict):
                        title = item.get("headline", "")
                        summary = item.get("summary", "")
                    else:
                        title = getattr(item, "headline", "")
                        summary = getattr(item, "summary", "")

                    if title:
                        headlines.append(f"Title: {title} | Summary: {summary}")
            else:
                logger.warning("Alpaca API keys not found, cannot fetch news.")

        # Compute sentiment score BEFORE appending the fallback display string (BUG-012)
        sentiment_score, sentiment_label = _compute_sentiment(headlines)

        if not headlines:
            headlines.append(f"No recent news found for {yf_ticker}.")

        payload = {
            "status": "success",
            "ticker": yf_ticker,
            "top_headlines": headlines,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
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
