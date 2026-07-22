from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.state import FinancialSwarmState
import json

class TickerExtraction(BaseModel):
    ticker: str = Field(description="The exact 1 to 5 letter stock ticker symbol (e.g., AAPL, TSLA, MSFT). If none is found, return 'UNKNOWN'.")

from langchain_core.messages import HumanMessage

async def sentiment_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {}

    ticker = state.get("current_ticker", "")
    if ticker == "UNKNOWN" or not ticker:
        return {"errors": ["Sentiment Agent: Could not resolve a valid ticker symbol from the state."]}

    import sys
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "src.servers.sentiment_server"])

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
