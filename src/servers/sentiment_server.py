import os
import re
import html
import json
import logging
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import yfinance as yf
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
    "upbeat", "momentum", "opportunity", "rebound", "advance", "win",
    "wins", "expansion", "deal", "partnership", "dividend", "bull",
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
    "fail", "fails", "failed", "halt", "halted", "probe", "delay", "delays",
}

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "without", "hardly", "barely",
    "fails", "failed", "fail", "lack", "lacks",
}

ASSET_ECOSYSTEM_MAP = {
    "TCS": {
        "name": "Tata Consultancy Services TCS",
        "indirect_query": "Indian IT services sector Infosys Wipro AI outsourcing US tech spending Nifty IT",
    },
    "RELIANCE": {
        "name": "Reliance Industries RIL",
        "indirect_query": "India oil refining telecom Jio retail crude oil prices Nifty 50 macro",
    },
    "INFY": {
        "name": "Infosys",
        "indirect_query": "Indian IT sector TCS Wipro enterprise cloud AI deal pipeline US client spending",
    },
    "HDFCBANK": {
        "name": "HDFC Bank",
        "indirect_query": "RBI interest rate policy Indian banking sector credit growth liquidity Nifty Bank",
    },
    "ICICIBANK": {
        "name": "ICICI Bank",
        "indirect_query": "RBI monetary policy Indian private banks credit growth NPA Nifty Bank",
    },
    "WIPRO": {
        "name": "Wipro",
        "indirect_query": "Indian IT services sector TCS Infosys global tech outsourcing demand",
    },
    "SBIN": {
        "name": "State Bank of India SBI",
        "indirect_query": "RBI repo rate Indian public sector banks PSU credit growth bond yields",
    },
    "TATAMOTORS": {
        "name": "Tata Motors JLR",
        "indirect_query": "India auto sector EV demand passenger vehicles global automotive supply chain",
    },
    "AAPL": {
        "name": "Apple AAPL",
        "indirect_query": "TSMC Foxconn global smartphone supply chain consumer electronics AI devices",
    },
    "NVDA": {
        "name": "Nvidia NVDA",
        "indirect_query": "AI data center capex TSMC HBM memory hyperscaler cloud GPU spending semiconductor",
    },
    "MSFT": {
        "name": "Microsoft MSFT",
        "indirect_query": "enterprise cloud computing Azure AWS Google Cloud AI software capex",
    },
    "GOOGL": {
        "name": "Alphabet Google GOOGL",
        "indirect_query": "digital advertising cloud computing generative AI search antitrust tech sector",
    },
    "GOOG": {
        "name": "Alphabet Google GOOG",
        "indirect_query": "digital advertising cloud computing generative AI search antitrust tech sector",
    },
    "META": {
        "name": "Meta Platforms META",
        "indirect_query": "digital ad spending social media AI infrastructure capex tech regulation",
    },
    "AMZN": {
        "name": "Amazon AMZN",
        "indirect_query": "US e-commerce consumer retail spending cloud AWS logistics supply chain",
    },
    "TSLA": {
        "name": "Tesla TSLA",
        "indirect_query": "global EV battery lithium supply chain autonomous driving BYD auto tariffs",
    },
    "BA": {
        "name": "Boeing BA",
        "indirect_query": "Airbus commercial aviation airlines jet demand FAA aerospace supply chain",
    },
    "BTC": {
        "name": "Bitcoin BTC",
        "indirect_query": "spot crypto ETF institutional inflows Federal Reserve liquidity SEC crypto regulation",
    },
    "ETH": {
        "name": "Ethereum ETH",
        "indirect_query": "DeFi layer-2 institutional crypto ETF SEC digital asset regulation macro liquidity",
    },
    "SOL": {
        "name": "Solana SOL",
        "indirect_query": "crypto altcoin liquidity institutional digital assets DeFi volume macro rates",
    },
}


def _clean_html_text(raw: str) -> str:
    if not raw:
        return ""
    unescaped = html.unescape(str(raw))
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()


def _score_text_tokens(text: str) -> tuple[int, int]:
    raw_tokens = [w.strip(".,!?;:\"'()[]{}") for w in text.lower().split()]
    tokens = [t for t in raw_tokens if t]

    bull = 0
    bear = 0
    for idx, word in enumerate(tokens):
        preceding = tokens[max(0, idx - 2) : idx]
        is_negated = any(p in NEGATION_WORDS for p in preceding)

        if word in BULLISH_KEYWORDS:
            if is_negated:
                bear += 1
            else:
                bull += 1
        elif word in BEARISH_KEYWORDS:
            if is_negated and word not in {"fail", "fails", "failed"}:
                bull += 1
            else:
                bear += 1
    return bull, bear


def _compute_sentiment(
    direct_headlines: list[str],
    indirect_headlines: list[str] | None = None,
) -> tuple[float, str]:
    indirect_headlines = indirect_headlines or []
    if not direct_headlines and not indirect_headlines:
        return 0.5, "NEUTRAL"

    weighted_bull = 0.0
    weighted_bear = 0.0

    for h in direct_headlines:
        b, m = _score_text_tokens(h)
        weighted_bull += b * 1.0
        weighted_bear += m * 1.0

    for h in indirect_headlines:
        b, m = _score_text_tokens(h)
        weighted_bull += b * 0.6
        weighted_bear += m * 0.6

    total_signals = weighted_bull + weighted_bear
    if total_signals <= 0:
        return 0.5, "NEUTRAL"

    raw_score = weighted_bull / total_signals
    confidence = min(total_signals / 7.0, 1.0)
    score = 0.5 + (raw_score - 0.5) * confidence
    score = max(0.05, min(0.95, score))

    if score > 0.6:
        label = "BULLISH"
    elif score < 0.4:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    return round(score, 3), label


def _fetch_google_news_rss(query: str, is_indian: bool = False, limit: int = 5) -> list[dict]:
    encoded_q = urllib.parse.quote(f"{query} when:7d")
    if is_indian:
        url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-IN&gl=IN&ceid=IN:en"
    else:
        url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    articles: list[dict] = []
    try:
        resp = requests.get(url, headers=headers, timeout=6.0)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item"):
            raw_title = item.findtext("title") or ""
            raw_desc = item.findtext("description") or ""
            raw_link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source_name = source_el.text.strip() if source_el is not None and source_el.text else "Financial News Wire"

            title = _clean_html_text(raw_title)
            desc = _clean_html_text(raw_desc)
            if desc.lower().startswith(title[:25].lower()):
                desc = desc[len(title):].strip(" -–—:|.")

            full_summary = (
                f"Source: {source_name}"
                f"{f' ({pub_date})' if pub_date else ''}. "
                f"{desc if len(desc) > 25 else f'{title}. Coverage reported via {source_name} tracking market momentum, institutional flows, and sector catalysts.'}"
            )

            if title:
                articles.append({
                    "title": title,
                    "summary": full_summary.strip(),
                    "url": raw_link,
                })
            if len(articles) >= limit:
                break
    except Exception as e:
        logger.debug("Google News RSS fetch warning for '%s': %s", query, e)

    return articles


def _fetch_yfinance_news(ticker_or_query: str, is_query: bool = False, limit: int = 5) -> list[dict]:
    articles: list[dict] = []
    try:
        if is_query and hasattr(yf, "Search"):
            search_obj = yf.Search(ticker_or_query, news_count=limit)
            raw_news = getattr(search_obj, "news", []) or []
        else:
            stock = yf.Ticker(ticker_or_query)
            raw_news = getattr(stock, "news", []) or []

        for item in raw_news[:limit]:
            if not isinstance(item, dict):
                continue
            content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
            title = _clean_html_text(content.get("title") or item.get("title") or "")
            summary = _clean_html_text(
                content.get("description")
                or content.get("summary")
                or item.get("summary")
                or ""
            )
            provider = (
                content.get("provider", {}).get("displayName")
                if isinstance(content.get("provider"), dict)
                else item.get("publisher") or "Yahoo Finance"
            )
            canonical_url = (
                content.get("canonicalUrl", {}).get("url")
                if isinstance(content.get("canonicalUrl"), dict)
                else item.get("link") or ""
            )
            if provider and summary and not summary.lower().startswith("source:"):
                summary = f"Source: {provider}. {summary}"
            elif provider and not summary:
                summary = f"Source: {provider}. {title}."

            if title:
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": str(canonical_url or "").strip(),
                })
    except Exception as e:
        logger.debug("yfinance news lookup warning for '%s': %s", ticker_or_query, e)

    return articles


def _resolve_ecosystem_queries(base_symbol: str, yf_ticker: str, is_indian: bool, asset_class: str) -> tuple[str, str]:
    if base_symbol in ASSET_ECOSYSTEM_MAP:
        entry = ASSET_ECOSYSTEM_MAP[base_symbol]
        direct_q = f"{entry['name']} stock" if asset_class != "crypto" else f"{entry['name']} crypto"
        return direct_q, entry["indirect_query"]

    company_name = base_symbol
    sector = ""
    industry = ""
    try:
        info = yf.Ticker(yf_ticker).info or {}
        company_name = info.get("shortName") or info.get("longName") or base_symbol
        sector = info.get("sector") or ""
        industry = info.get("industry") or ""
    except Exception:
        pass

    if asset_class == "crypto":
        direct_q = f"{company_name} cryptocurrency market"
        indirect_q = "crypto institutional ETF inflows Federal Reserve liquidity SEC digital asset regulation"
    elif is_indian:
        direct_q = f"{company_name} {base_symbol} NSE BSE share price"
        if sector or industry:
            indirect_q = f"India {sector} {industry} sector outlook RBI policy Nifty 50 macro"
        else:
            indirect_q = "Indian stock market Nifty 50 Sensex FII DII flows RBI monetary policy"
    else:
        direct_q = f"{company_name} {base_symbol} stock earnings"
        if sector or industry:
            indirect_q = f"US {sector} {industry} supply chain sector outlook Wall Street macro"
        else:
            indirect_q = "US stock market S&P 500 Federal Reserve interest rates institutional flows"

    return direct_q, indirect_q


def _format_article_line(prefix: str, item: dict) -> str:
    url_part = f" | URL: {item['url']}" if item.get("url") else ""
    return f"Title: [{prefix}] {item['title']} | Summary: {item['summary']}{url_part}"


@mcp.tool()
def analyze_market_sentiment(ticker: str, asset_class: str = "equity") -> str:
    """Fetches both Direct asset news (3 items) and Indirectly Related sector/macro news (>=2 items)."""
    ticker_upper = "".join(
        e for e in ticker.upper() if e.isalnum() or e in ["-", "/", "."]
    )

    is_indian_market = ticker_upper.endswith(".NS") or ticker_upper.endswith(".BO")

    if is_indian_market:
        yf_ticker = ticker_upper
        base_symbol = ticker_upper.rsplit(".", 1)[0]
    else:
        clean_ticker = ticker_upper.replace("/", "-")
        base_symbol = clean_ticker.split("-")[0]
        if asset_class == "crypto" or "-" in ticker_upper or "/" in ticker_upper:
            yf_ticker = clean_ticker if "-USD" in clean_ticker else f"{clean_ticker}-USD"
        else:
            yf_ticker = clean_ticker

    try:
        direct_query, indirect_query = _resolve_ecosystem_queries(
            base_symbol=base_symbol,
            yf_ticker=yf_ticker,
            is_indian=is_indian_market,
            asset_class=asset_class,
        )

        direct_items: list[dict] = []
        seen_titles: set[str] = set()

        def _add_unique(target_list: list[dict], candidates: list[dict], max_items: int):
            for c in candidates:
                if len(target_list) >= max_items:
                    break
                norm_t = c["title"].lower()[:55].strip()
                if norm_t and norm_t not in seen_titles:
                    seen_titles.add(norm_t)
                    target_list.append(c)

        # 1. Direct News
        if not is_indian_market:
            api_key = os.environ.get("ALPACA_API_KEY")
            secret_key = os.environ.get("ALPACA_SECRET_KEY")
            if api_key and secret_key:
                try:
                    from alpaca.data.historical import NewsClient
                    from alpaca.data.requests import NewsRequest

                    client = NewsClient(api_key, secret_key)
                    req = NewsRequest(symbols=ticker_upper.replace("-", "/"), limit=4, include_content=True)
                    news_items = client.get_news(req)
                    items_list = (
                        news_items.news
                        if hasattr(news_items, "news")
                        else news_items.dict().get("news", [])
                        if hasattr(news_items, "dict")
                        else []
                    )
                    alpaca_candidates = []
                    for item in items_list:
                        t = _clean_html_text(
                            item.get("headline", "") if isinstance(item, dict) else getattr(item, "headline", "")
                        )
                        s = _clean_html_text(
                            item.get("summary", "") if isinstance(item, dict) else getattr(item, "summary", "")
                        )
                        body = _clean_html_text(
                            item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")
                        )
                        url = (
                            item.get("url", "") if isinstance(item, dict) else getattr(item, "url", "")
                        )
                        source = (
                            item.get("source", "Benzinga / Alpaca Wire")
                            if isinstance(item, dict)
                            else getattr(item, "source", "Benzinga / Alpaca Wire")
                        )
                        full_text = body if len(body) > len(s) else s
                        if full_text:
                            full_text = f"Source: {source}. {full_text[:900]}"
                        else:
                            full_text = f"Source: {source}. {t}"
                        if t:
                            alpaca_candidates.append({"title": t, "summary": full_text, "url": str(url or "")})
                    _add_unique(direct_items, alpaca_candidates, max_items=3)
                except Exception as e:
                    logger.debug("Alpaca direct news warning for %s: %s", ticker_upper, e)

        if len(direct_items) < 3:
            _add_unique(direct_items, _fetch_yfinance_news(yf_ticker, is_query=False, limit=4), max_items=3)
        if len(direct_items) < 3:
            _add_unique(direct_items, _fetch_yfinance_news(direct_query, is_query=True, limit=4), max_items=3)
        if len(direct_items) < 3:
            _add_unique(
                direct_items,
                _fetch_google_news_rss(direct_query, is_indian=is_indian_market, limit=4),
                max_items=3,
            )

        # 2. Indirect Sector & Macro News (Guarantees >= 2 items)
        indirect_items: list[dict] = []
        _add_unique(
            indirect_items,
            _fetch_google_news_rss(indirect_query, is_indian=is_indian_market, limit=5),
            max_items=3,
        )
        if len(indirect_items) < 2:
            _add_unique(
                indirect_items,
                _fetch_yfinance_news(indirect_query, is_query=True, limit=4),
                max_items=3,
            )

        formatted_direct = [_format_article_line("DIRECT", item) for item in direct_items[:3]]
        formatted_indirect = [_format_article_line("INDIRECT", item) for item in indirect_items[:3]]

        sentiment_score, sentiment_label = _compute_sentiment(
            direct_headlines=[f"{i['title']} {i['summary']}" for i in direct_items[:3]],
            indirect_headlines=[f"{i['title']} {i['summary']}" for i in indirect_items[:3]],
        )

        combined_headlines = formatted_direct + formatted_indirect
        if not combined_headlines:
            combined_headlines.append(f"No recent news found for {yf_ticker}.")

        payload = {
            "status": "success",
            "ticker": yf_ticker,
            "top_headlines": combined_headlines,
            "direct_count": len(formatted_direct),
            "indirect_count": len(formatted_indirect),
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
        }

        return json.dumps(payload, indent=2)
    except Exception as e:
        logger.exception("Sentiment server failed for %s", ticker_upper)
        return json.dumps(
            {
                "status": "error",
                "message": f"Failed to retrieve news: {str(e)}",
            }
        )


if __name__ == "__main__":
    mcp.run()
