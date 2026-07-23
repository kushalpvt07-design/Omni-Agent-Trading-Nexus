from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import FinancialSwarmState
from langchain_core.messages import HumanMessage

class TickerExtraction(BaseModel):
    ticker: str = Field(description="The exact stock ticker symbol or crypto pair (e.g., AAPL, BTC/USD). If none is found, return 'UNKNOWN'.")
    asset_class: str = Field(description="Must be 'crypto' or 'equity'")

import re

async def parser_node(state: FinancialSwarmState) -> dict:
    latest_message = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            latest_message = msg.content
            break

    # 1. Deterministic Regex Extraction (0 API calls, 0 ms delay)
    tickers = re.findall(r'\b[A-Z]{1,5}\b', latest_message)
    # Exclude common English false positives
    tickers = [t for t in tickers if t not in {"BUY", "SELL", "A", "I", "FOR", "THE", "OF", "TO", "IN"}]
    
    crypto_assets = {"BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "DOT", "LINK"}
    
    if tickers:
        ticker = tickers[0]
        if ticker in crypto_assets:
            return {"current_ticker": f"{ticker}/USD", "asset_class": "crypto"}
        return {"current_ticker": ticker, "asset_class": "equity"}

    # 2. Fallback to LLM only if Regex fails (or input is natural language company name)
    models_to_try = [
        "gemini-3.5-flash",
        "gemini-3-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash"
    ]
    
    primary_llm = ChatGoogleGenerativeAI(model=models_to_try[0], temperature=0.0)
    structured_extractor = primary_llm.with_structured_output(TickerExtraction)
    
    fallbacks = [
        ChatGoogleGenerativeAI(model=m, temperature=0.0).with_structured_output(TickerExtraction)
        for m in models_to_try[1:]
    ]
    structured_extractor = structured_extractor.with_fallbacks(fallbacks)
    
    try:
        extraction = await structured_extractor.ainvoke(
            f"You are a strict financial entity extractor. Extract the OFFICIAL stock market ticker symbol or crypto pair from this message. "
            f"CRITICAL: You must convert company names to their actual market tickers (e.g., 'tesla' MUST become 'TSLA'). "
            f"For cryptocurrencies, use the Alpaca format with a slash (e.g., 'bitcoin' MUST become 'BTC/USD'). "
            f"Message: '{latest_message}'"
        )
        ticker = extraction.ticker.strip(" \n\"'").upper()
        asset_class = extraction.asset_class.strip().lower()
    except Exception as e:
        # Force graph termination by injecting an error
        return {"errors": [f"Parser Extraction Failed: {str(e)}"]}
    
    if ticker == "UNKNOWN" or not ticker:
        # Halt the graph instead of passing garbage downstream
        return {"errors": ["Parser Agent: Could not resolve a valid ticker symbol. Halting execution."]}

    return {"current_ticker": ticker, "asset_class": asset_class}
