from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.state import FinancialSwarmState
import os

# Define the strict extraction schema
class TickerExtraction(BaseModel):
    ticker: str = Field(description="The exact 1 to 5 letter stock ticker symbol (e.g., AAPL, TSLA, MSFT). If none is found, return 'UNKNOWN'.")

from langchain_core.messages import HumanMessage

async def quant_agent_node(state: FinancialSwarmState) -> dict:
    latest_message = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            latest_message = msg.content
            break

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
        return {"errors": [f"Quant Agent Extraction Failed: {str(e)}"]}
    
    if ticker == "UNKNOWN" or not ticker:
        return {"errors": ["Quant Agent: Could not resolve a valid ticker symbol from the prompt."]}

    # --- The Original MCP Server Call ---
    server_params = StdioServerParameters(command="python", args=["-m", "src.servers.quant_server"])

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("get_daily_close_price", arguments={"ticker": ticker})
                
                text_content = result.content[0].text if isinstance(result.content, list) else result.content
                # UPDATE: Pass current_ticker out to the state graph
                return {
                    "quant_data": {ticker: text_content},
                    "current_ticker": ticker
                }
    except Exception as e:
        return {"errors": [f"Quant Server Error: {str(e)}"]}
