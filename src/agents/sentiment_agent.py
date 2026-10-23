import sys
import json
import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import retry, stop_after_attempt, wait_exponential
from src.state import FinancialSwarmState
from src.core.telemetry import Timer, telemetry

logger = logging.getLogger("omni-nexus.sentiment")

MCP_TIMEOUT_SECONDS = 15.0


async def _fetch_mcp_sentiment_inner(ticker: str, asset_class: str) -> str:
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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    reraise=True,
)
async def fetch_mcp_sentiment_data(ticker: str, asset_class: str) -> str:
    return await asyncio.wait_for(
        _fetch_mcp_sentiment_inner(ticker, asset_class),
        timeout=MCP_TIMEOUT_SECONDS,
    )


async def sentiment_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {}

    ticker = state.get("current_ticker", "")
    asset_class = state.get("asset_class", "equity")

    if ticker == "UNKNOWN" or not ticker:
        telemetry.record_error("SENTIMENT_INVALID_TICKER")
        return {
            "errors": [
                "Sentiment Agent: Could not resolve a valid ticker symbol from the state."
            ]
        }

    with Timer("sentiment_agent_node") as timer:
        try:
            text_content = await fetch_mcp_sentiment_data(ticker, asset_class)

            if not text_content or text_content.strip() == "":
                text_content = "{}"

            try:
                parsed_result = json.loads(text_content)
                if isinstance(parsed_result, dict) and parsed_result.get("status") == "error":
                    raise RuntimeError(parsed_result.get("message", "Sentiment tool returned error"))
                final_data = parsed_result
            except json.JSONDecodeError:
                final_data = {
                    "status": "degraded",
                    "ticker": ticker,
                    "top_headlines": [text_content],
                    "sentiment_score": 0.5,
                    "sentiment_label": "NEUTRAL",
                }

            return {
                "sentiment_data": {ticker: final_data},
                "node_latencies_ms": {"sentiment_agent_node": timer.elapsed_ms},
            }
        except Exception as e:
            telemetry.record_error("SENTIMENT_DEGRADED")
            logger.warning(
                "Sentiment branch failed for %s — degrading gracefully to NEUTRAL: %s",
                ticker, e,
            )
            degraded_data = {
                "status": "degraded",
                "ticker": ticker,
                "top_headlines": [
                    f"[DEGRADED TELEMETRY] News sentiment unavailable ({str(e)}). Relying on quantitative data."
                ],
                "sentiment_score": 0.5,
                "sentiment_label": "NEUTRAL",
                "warning": f"Sentiment branch failed: {str(e)}",
            }
            return {
                "sentiment_data": {ticker: degraded_data},
                "node_latencies_ms": {"sentiment_agent_node": timer.elapsed_ms},
            }
