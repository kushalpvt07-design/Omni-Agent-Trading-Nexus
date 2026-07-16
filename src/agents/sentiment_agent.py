from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.state import FinancialSwarmState
import json

class TickerExtraction(BaseModel):
    ticker: str = Field(description="The exact 1 to 5 letter stock ticker symbol (e.g., AAPL, TSLA, MSFT). If none is found, return 'UNKNOWN'.")

async def sentiment_agent_node(state: FinancialSwarmState) -> dict:
    latest_message = state["messages"][-1].content if state["messages"] else ""
    
    # --- The LLM Extractor Upgrade ---
    extractor_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
    structured_extractor = extractor_llm.with_structured_output(TickerExtraction)
    
    try:
        extraction = await structured_extractor.ainvoke(
            f"You are a strict financial entity extractor. Extract the OFFICIAL stock market ticker symbol from this message. "
            f"CRITICAL: You must convert company names to their actual market tickers (e.g., 'tesla' MUST become 'TSLA', 'apple' MUST become 'AAPL'). "
            f"Message: '{latest_message}'"
        )
        ticker = extraction.ticker.upper()
    except Exception as e:
        return {"errors": [f"Sentiment Agent Extraction Failed: {str(e)}"]}
    
    if ticker == "UNKNOWN" or not ticker:
        return {} # Let the Quant agent throw the missing ticker error to the UI

    # --- The Original MCP Server Call ---
    server_params = StdioServerParameters(command="python", args=["-m", "src.servers.sentiment_server"])

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("analyze_market_sentiment", arguments={"ticker": ticker})
                
                text_content = result.content[0].text if isinstance(result.content, list) else result.content
                try:
                    parsed_result = json.loads(text_content)
                    return {"sentiment_data": {ticker: parsed_result}}
                except Exception:
                    return {"sentiment_data": {ticker: {"raw_output": text_content}}}
    except Exception as e:
        return {"errors": [f"Sentiment Agent Server Error: {str(e)}"]}
