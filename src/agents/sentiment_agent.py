import sys
import json
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import retry, stop_after_attempt, wait_exponential
from src.state import FinancialSwarmState

logger = logging.getLogger("omni-nexus.sentiment")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def fetch_mcp_sentiment_data(ticker: str, asset_class: str) -> str:
    server_params = StdioServerParameters(
        command=sys.executable, args=["-m", "src.servers.sentiment_server"]
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "analyze_market_sentiment",
                arguments={"ticker": ticker, "asset_class": asset_class},
            )

            if getattr(result, "isError", False):
                raise RuntimeError(f"MCP Server Internal Error: {result.content}")

            if isinstance(result.content, list):
                return result.content[0].text if len(result.content) > 0 else "{}"

            return str(result.content)


async def sentiment_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {}

    ticker = state.get("current_ticker", "")
    asset_class = state.get("asset_class", "equity")

    if ticker == "UNKNOWN" or not ticker:
        return {
            "errors": [
                "Sentiment Agent: Could not resolve a valid ticker symbol from the state."
            ]
        }

    try:
        text_content = await fetch_mcp_sentiment_data(ticker, asset_class)

        if not text_content or text_content.strip() == "":
            text_content = "{}"

        try:
            parsed_result = json.loads(text_content)
            final_data = parsed_result
        except Exception:
            final_data = {"raw_output": text_content}

        # Nest data under the ticker key so the Orchestrator can read it
        return {"sentiment_data": {ticker: final_data}}
    except Exception as e:
        return {"errors": [f"Sentiment Agent Server Error: {str(e)}"]}
