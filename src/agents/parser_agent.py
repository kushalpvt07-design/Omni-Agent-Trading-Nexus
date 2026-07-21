from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import FinancialSwarmState
from langchain_core.messages import HumanMessage

class TickerExtraction(BaseModel):
    ticker: str = Field(description="The exact 1 to 5 letter stock ticker symbol (e.g., AAPL, TSLA, MSFT). If none is found, return 'UNKNOWN'.")

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
    
    if tickers:
        return {"current_ticker": tickers[0]}

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
            f"You are a strict financial entity extractor. Extract the OFFICIAL stock market ticker symbol from this message. "
            f"CRITICAL: You must convert company names to their actual market tickers (e.g., 'tesla' MUST become 'TSLA', 'apple' MUST become 'AAPL'). "
            f"Message: '{latest_message}'"
        )
        ticker = extraction.ticker.upper()
    except Exception as e:
        return {"errors": [f"Parser Agent Extraction Failed: {str(e)}"]}
    
    if ticker == "UNKNOWN" or not ticker:
        return {"errors": ["Parser Agent: Could not resolve a valid ticker symbol from the prompt."]}

    return {"current_ticker": ticker}
