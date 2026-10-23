import sys
import json
import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_not_exception_type,
)
from src.state import FinancialSwarmState
from src.core.telemetry import Timer, telemetry

logger = logging.getLogger("omni-nexus.quant")

_NON_RETRYABLE_ERRORS = {"AUTH_ERROR", "INVALID_TICKER", "DATA_CORRUPT", "NO_DATA"}
MCP_TIMEOUT_SECONDS = 15.0


class AlpacaAuthError(Exception):
    """Raised when Alpaca returns a 401/403 or deterministic data failure — retrying won't help."""
    pass


async def _fetch_mcp_quant_inner(ticker: str, asset_class: str) -> str:
    server_params = StdioServerParameters(
        command=sys.executable, args=["-m", "src.servers.quant_server"]
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_daily_close_price",
                arguments={"ticker": ticker, "asset_class": asset_class},
            )

            if getattr(result, "isError", False):
                raise RuntimeError(f"MCP Server Internal Error: {result.content}")

            if isinstance(result.content, list):
                raw_text = result.content[0].text if len(result.content) > 0 else "{}"
            else:
                raw_text = str(result.content)

            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict) and parsed.get("status") == "error":
                    error_code = parsed.get("error_code", "UNKNOWN")
                    error_msg = parsed.get("message", "Unknown quant server error.")

                    if error_code in _NON_RETRYABLE_ERRORS:
                        raise AlpacaAuthError(f"[{error_code}] {error_msg}")
                    raise RuntimeError(f"[{error_code}] {error_msg}")
            except AlpacaAuthError:
                raise
            except (json.JSONDecodeError, TypeError):
                pass

            return raw_text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    reraise=True,
    retry=retry_if_not_exception_type(AlpacaAuthError),
)
async def fetch_mcp_quant_data(ticker: str, asset_class: str) -> str:
    return await asyncio.wait_for(
        _fetch_mcp_quant_inner(ticker, asset_class),
        timeout=MCP_TIMEOUT_SECONDS,
    )


async def quant_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {}

    ticker = state.get("current_ticker", "")
    asset_class = state.get("asset_class", "equity")

    if ticker == "UNKNOWN" or not ticker:
        telemetry.record_error("QUANT_INVALID_TICKER")
        return {
            "errors": [
                "Quant Agent: Could not resolve a valid ticker symbol from the state."
            ]
        }

    with Timer("quant_agent_node") as timer:
        try:
            text_content = await fetch_mcp_quant_data(ticker, asset_class)

            if not text_content or text_content.strip() == "":
                text_content = "{}"

            return {
                "quant_data": {ticker: text_content},
                "node_latencies_ms": {"quant_agent_node": timer.elapsed_ms},
            }

        except AlpacaAuthError as e:
            telemetry.record_error("QUANT_NON_RETRYABLE_ERROR")
            logger.error("Quant deterministic/auth failure for %s: %s", ticker, e)
            return {
                "errors": [f"Quant Agent [{ticker}]: {str(e)}"],
                "node_latencies_ms": {"quant_agent_node": timer.elapsed_ms},
            }
        except Exception as e:
            telemetry.record_error("QUANT_SERVER_ERROR")
            logger.exception("Quant agent error for %s", ticker)
            return {
                "errors": [f"Quant Server Error [{ticker}]: {str(e)}"],
                "node_latencies_ms": {"quant_agent_node": timer.elapsed_ms},
            }
