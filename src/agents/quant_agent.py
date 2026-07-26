import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import retry, stop_after_attempt, wait_exponential
from src.state import FinancialSwarmState

# FIX 2: Wrapped the brittle MCP subprocess in a proper retry block
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def fetch_mcp_quant_data(ticker: str, asset_class: str) -> str:
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "src.servers.quant_server"])
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_daily_close_price", 
                arguments={"ticker": ticker, "asset_class": asset_class}
            )
            
            if getattr(result, "isError", False):
                raise RuntimeError(f"MCP Server Internal Error: {result.content}")
            
            if isinstance(result.content, list):
                return result.content[0].text if len(result.content) > 0 else "{}"
            
            return str(result.content)

async def quant_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {}

    ticker = state.get("current_ticker", "")
    asset_class = state.get("asset_class", "equity")
    
    if ticker == "UNKNOWN" or not ticker:
        return {"errors": ["Quant Agent: Could not resolve a valid ticker symbol from the state."]}

    try:
        text_content = await fetch_mcp_quant_data(ticker, asset_class)
        
        # FIX 3: Prevent passing empty/None strings to Risk Desk to avoid JSONDecodeErrors
        if not text_content or text_content.strip() == "":
            text_content = "{}"
            
        return {
            "quant_data": {ticker: text_content}
        }
    except Exception as e:
        return {"errors": [f"Quant Server Error: {str(e)}"]}
