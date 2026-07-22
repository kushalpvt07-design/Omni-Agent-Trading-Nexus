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
    ticker = state.get("current_ticker", "")
    asset_class = state.get("asset_class", "equity")
    if ticker == "UNKNOWN" or not ticker:
        return {"errors": ["Quant Agent: Could not resolve a valid ticker symbol from the state."]}

    import sys
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "src.servers.quant_server"])

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("get_daily_close_price", arguments={"ticker": ticker, "asset_class": asset_class})
                
                text_content = result.content[0].text if isinstance(result.content, list) else result.content
                # UPDATE: Pass current_ticker out to the state graph
                return {
                    "quant_data": {ticker: text_content},
                    "current_ticker": ticker
                }
    except Exception as e:
        return {"errors": [f"Quant Server Error: {str(e)}"]}
