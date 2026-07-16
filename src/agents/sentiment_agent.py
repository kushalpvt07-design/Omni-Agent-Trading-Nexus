from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.state import FinancialSwarmState
import json

async def sentiment_agent_node(state: FinancialSwarmState) -> dict:
    latest_message = state["messages"][-1].content if state["messages"] else ""
    words = latest_message.split()
    ticker = next((word.upper() for word in words if len(word) <= 5 and word.isalpha()), None)
    
    if not ticker:
        return {} # Let the Quant agent handle the missing ticker error

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
        return {"errors": [f"Sentiment Agent Error: {str(e)}"]}
