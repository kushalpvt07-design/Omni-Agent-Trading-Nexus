from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import FinancialSwarmState
from langchain_core.messages import HumanMessage

class TickerExtraction(BaseModel):
    ticker: str = Field(description="The exact 1 to 5 letter stock ticker symbol (e.g., AAPL, TSLA, MSFT). If none is found, return 'UNKNOWN'.")

async def parser_node(state: FinancialSwarmState) -> dict:
    latest_message = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            latest_message = msg.content
            break

    extractor_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.0)
    structured_extractor = extractor_llm.with_structured_output(TickerExtraction)
    
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
