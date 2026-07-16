from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.state import FinancialSwarmState

async def quant_agent_node(state: FinancialSwarmState) -> dict:
    latest_message = state["messages"][-1].content if state["messages"] else ""
    words = latest_message.split()
    ticker = next((word.upper() for word in words if len(word) <= 5 and word.isalpha()), None)
    
    if not ticker:
        return {"errors": ["Quant Agent: Could not resolve a valid ticker symbol."]}

    server_params = StdioServerParameters(command="python", args=["-m", "src.servers.quant_server"])

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("get_daily_close_price", arguments={"ticker": ticker})
                
                # RETURN ONLY THE DELTA
                # Note: Handling list text content as established previously to prevent crashes
                text_content = result.content[0].text if isinstance(result.content, list) else result.content
                return {"quant_data": {ticker: text_content}}
    except Exception as e:
        return {"errors": [f"Quant Agent Error: {str(e)}"]}
