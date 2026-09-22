import sys
import json
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

logger = logging.getLogger("omni-nexus.quant")

# Error codes that should NOT be retried (permanent failures)
_NON_RETRYABLE_ERRORS = {"AUTH_ERROR", "INVALID_TICKER"}


class AlpacaAuthError(Exception):
    """Raised when Alpaca returns a 401/403 — retrying won't help."""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
    retry=retry_if_not_exception_type(AlpacaAuthError),
)
async def fetch_mcp_quant_data(ticker: str, asset_class: str) -> str:
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

            # Parse structured errors from the quant server and raise typed
            # exceptions so the retry decorator can decide whether to retry.
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict) and parsed.get("status") == "error":
                    error_code = parsed.get("error_code", "UNKNOWN")
                    error_msg = parsed.get("message", "Unknown quant server error.")

                    if error_code in _NON_RETRYABLE_ERRORS:
                        raise AlpacaAuthError(
                            f"[{error_code}] {error_msg}"
                        )
                    # Retryable server errors — raise so tenacity can retry
                    raise RuntimeError(f"[{error_code}] {error_msg}")
            except AlpacaAuthError:
                raise  # Propagate non-retryable errors immediately
            except (json.JSONDecodeError, TypeError):
                pass  # Not JSON — return as-is

            return raw_text


async def quant_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {}

    ticker = state.get("current_ticker", "")
    asset_class = state.get("asset_class", "equity")

    if ticker == "UNKNOWN" or not ticker:
        return {
            "errors": [
                "Quant Agent: Could not resolve a valid ticker symbol from the state."
            ]
        }

    try:
        text_content = await fetch_mcp_quant_data(ticker, asset_class)

        # Prevent passing empty/None strings to Risk Desk
        if not text_content or text_content.strip() == "":
            text_content = "{}"

        return {"quant_data": {ticker: text_content}}

    except AlpacaAuthError as e:
        logger.error("Alpaca auth failure for %s — not retrying: %s", ticker, e)
        return {
            "errors": [
                f"Quant Agent [{ticker}]: {str(e)} — "
                "Please regenerate your Alpaca API keys and update the .env file."
            ]
        }
    except Exception as e:
        logger.exception("Quant agent error for %s", ticker)
        return {"errors": [f"Quant Server Error [{ticker}]: {str(e)}"]}

