import json
import logging
import yfinance as yf
import requests
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("omni-nexus.sentiment-server")

mcp = FastMCP("SentimentServer")

# ── Keyword-based sentiment scoring ─────────────────────────────
BULLISH_KEYWORDS = [
    "surge", "surges", "surging", "rally", "rallies", "rallying",
    "gain", "gains", "gained", "rise", "rises", "rising", "soar",
    "soars", "soaring", "jump", "jumps", "jumped", "boost", "boosts",
    "bullish", "upgrade", "upgrades", "upgraded", "beat", "beats",
    "outperform", "record", "high", "breakout", "growth", "profit",
    "strong", "buy", "positive", "optimistic", "recover", "recovery",
    "upbeat", "momentum", "opportunity", "rebound", "advance",
]

BEARISH_KEYWORDS = [
    "drop", "drops", "dropped", "fall", "falls", "falling", "decline",
    "declines", "declining", "crash", "crashes", "crashing", "plunge",
    "plunges", "plunging", "loss", "losses", "sink", "sinks", "sinking",
    "bearish", "downgrade", "downgrades", "downgraded", "miss", "misses",
    "underperform", "low", "sell", "selloff", "sell-off", "negative",
    "pessimistic", "risk", "warning", "fear", "weak", "slump", "tumble",
    "concern", "concerns", "worried", "recession", "layoff", "layoffs",
    "cut", "cuts", "deficit", "debt", "fraud", "scandal", "lawsuit",
]


def _compute_sentiment(headlines: list[str]) -> tuple[float, str]:
    """Compute a sentiment score (0-1) and label from headline text."""
    if not headlines:
        return 0.5, "NEUTRAL"

    combined_text = " ".join(headlines).lower()
    words = combined_text.split()

    bullish_count = sum(1 for w in words if w.strip(".,!?;:\"'()") in BULLISH_KEYWORDS)
    bearish_count = sum(1 for w in words if w.strip(".,!?;:\"'()") in BEARISH_KEYWORDS)

    total_signals = bullish_count + bearish_count
    if total_signals == 0:
        return 0.5, "NEUTRAL"

    # Raw ratio biased toward bullish (1.0) or bearish (0.0)
    raw_score = bullish_count / total_signals

    # Dampen toward 0.5 for low-confidence results (few signals)
    confidence = min(total_signals / 8, 1.0)  # Full confidence at 8+ signals
    score = 0.5 + (raw_score - 0.5) * confidence

    # Clamp to [0.05, 0.95] to avoid absolute extremes
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
    """Fetches real market news using yfinance for sentiment analysis."""
    ticker_upper = "".join(
        e for e in ticker.upper() if e.isalnum() or e in ["-", "/", "."]
    )

    # Detect Indian market exchange suffixes
    is_indian_market = ticker_upper.endswith(".NS") or ticker_upper.endswith(".BO")

    if is_indian_market:
        # Use ticker as-is for Yahoo Finance (e.g. RELIANCE.NS)
        yf_ticker = ticker_upper
    else:
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

        # Compute sentiment score from headline content
        sentiment_score, sentiment_label = _compute_sentiment(headlines)

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
