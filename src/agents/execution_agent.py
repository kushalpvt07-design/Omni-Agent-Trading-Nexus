import uuid
import asyncio
import logging
from langchain_core.messages import AIMessage
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from src.state import FinancialSwarmState
from src.core.config import settings
from src.core.market_data import to_usd_price
from src.core.telemetry import Timer, telemetry
from src.persistence.user_portfolio import update_user_ledger

logger = logging.getLogger("omni-nexus.execution")


async def execution_agent_node(state: FinancialSwarmState) -> dict:
    with Timer("execution_agent_node") as timer:
        if not state.get("risk_approved", False):
            return {
                "messages": [
                    AIMessage(content="Execution skipped: Risk Desk rejected the trade.")
                ],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }

        if state.get("requires_human_approval", True) and not state.get("human_approved", False):
            return {
                "messages": [
                    AIMessage(content="Execution stalled: Waiting for explicit human approval.")
                ],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }

        trade = state.get("proposed_trade", {})
        action = trade.get("action", "HOLD")
        ticker = trade.get("ticker", "")
        live_price = float(trade.get("estimated_price", 0.0) or 0.0)
        user_id = state.get("user_id")

        if action in ["HOLD", "REJECT"] or live_price <= 0:
            return {
                "messages": [
                    AIMessage(content="Execution Engine: No action taken. Holding position.")
                ],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }

        raw_shares = trade.get("shares")
        shares = round(float(raw_shares), 4) if raw_shares is not None else 0.0

        if shares <= 0:
            telemetry.record_execution_outcome(False, "ZERO_SHARE_QUANTITY")
            return {
                "errors": ["Execution Engine: Share quantity is 0 or invalid. Trade aborted."],
                "messages": [AIMessage(content="Execution Engine aborted: Share quantity is 0.")],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }

        trade["shares"] = shares
        is_paper = state.get("paper_trading_enabled", True)

        if "." in ticker:
            if is_paper:
                try:
                    price_usd = await asyncio.to_thread(to_usd_price, live_price, ticker)
                    if user_id is not None:
                        update_user_ledger(
                            user_id=user_id,
                            action=action,
                            ticker=ticker,
                            shares=shares,
                            price=price_usd,
                            reasoning=trade.get("reasoning"),
                            alpaca_order_id=f"paper-inr-{uuid.uuid4().hex[:10]}",
                        )
                    telemetry.record_execution_outcome(True)
                    return {
                        "proposed_trade": trade,
                        "messages": [
                            AIMessage(
                                content=(
                                    f"Paper Trade Logged: {action} {shares} shares of {ticker} @ "
                                    f"₹{live_price:,.2f} (${price_usd:,.2f} USD). Note: Alpaca broker supports "
                                    f"US markets only — this trade was recorded in the paper ledger."
                                )
                            )
                        ],
                        "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
                    }
                except Exception as e:
                    telemetry.record_execution_outcome(False, "LEDGER_ERROR")
                    return {
                        "errors": [f"Execution Ledger Error: {str(e)}"],
                        "messages": [AIMessage(content=f"Execution Ledger Error: {str(e)}")],
                        "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
                    }

            return {
                "messages": [
                    AIMessage(
                        content=(
                            f"Execution Engine: Skipping Alpaca submission for international stock "
                            f"'{ticker}'. Alpaca supports US markets only."
                        )
                    )
                ],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }

        asset_class = state.get("asset_class", "equity")
        api_key = settings.ALPACA_API_KEY
        sec_key = settings.ALPACA_SECRET_KEY

        if not api_key or not sec_key:
            telemetry.record_execution_outcome(False, "MISSING_CREDENTIALS")
            return {
                "errors": ["Execution Engine: Missing Alpaca API credentials."],
                "messages": [AIMessage(content="Execution Engine aborted: Missing API credentials.")],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }

        client = TradingClient(api_key, sec_key, paper=is_paper)
        tif = TimeInForce.GTC if asset_class == "crypto" or "/" in ticker else TimeInForce.DAY
        client_order_id = f"nexus-{user_id or 0}-{ticker.replace('/', '')}-{uuid.uuid4().hex[:10]}"

        order_data = MarketOrderRequest(
            symbol=ticker,
            qty=shares,
            side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
            time_in_force=tif,
            client_order_id=client_order_id,
        )

        try:
            order = await asyncio.to_thread(client.submit_order, order_data)
            mode = "PAPER" if is_paper else "LIVE"

            filled_price = live_price
            raw_filled_price = getattr(order, "filled_avg_price", None)
            if raw_filled_price is not None:
                try:
                    parsed_fill = float(raw_filled_price)
                    if parsed_fill > 0:
                        filled_price = parsed_fill
                except (ValueError, TypeError):
                    pass

            if user_id is not None:
                update_user_ledger(
                    user_id=user_id,
                    action=action,
                    ticker=ticker,
                    shares=shares,
                    price=filled_price,
                    reasoning=trade.get("reasoning"),
                    alpaca_order_id=str(order.id),
                )

            telemetry.record_execution_outcome(True)
            logger.info(
                "Order executed (%s): %s %s shares of %s @ $%.2f — Alpaca ID: %s (user=%s)",
                mode, action, shares, ticker, filled_price, order.id, user_id,
            )

            return {
                "proposed_trade": trade,
                "messages": [
                    AIMessage(
                        content=(
                            f"Order executed ({mode}): {action} {shares} shares of {ticker} "
                            f"@ ${filled_price:,.2f}. Alpaca Order ID: {order.id}. Ledger Updated."
                        )
                    )
                ],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }
        except Exception as e:
            error_str = str(e).lower()
            is_auth = any(
                s in error_str for s in ("401", "403", "unauthorized", "forbidden")
            )

            if is_auth:
                telemetry.record_execution_outcome(False, "ALPACA_AUTH_ERROR")
                logger.error(
                    "AUTH_ERROR during execution for %s %s %s — "
                    "regenerate Alpaca keys at https://app.alpaca.markets/",
                    action, shares, ticker,
                )
                return {
                    "errors": [
                        f"Execution Engine AUTH_ERROR: Alpaca rejected credentials "
                        f"while submitting {action} {shares} {ticker}. "
                        f"Regenerate your API keys and update the .env file."
                    ],
                    "messages": [
                        AIMessage(
                            content=(
                                f"🚨 **Execution Engine: Authentication Failed**\n\n"
                                f"Alpaca rejected your API credentials (HTTP 401/403) "
                                f"when attempting to submit: **{action} {shares} shares of {ticker}**.\n\n"
                                f"**Fix:** Regenerate your API keys at https://app.alpaca.markets/ "
                                f"and update `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` in your `.env` file."
                            )
                        )
                    ],
                    "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
                }

            telemetry.record_execution_outcome(False, "ALPACA_API_ERROR")
            logger.exception("Alpaca API Error for %s %s %s", action, shares, ticker)
            return {
                "errors": [f"Alpaca API Error: {str(e)}"],
                "messages": [AIMessage(content=f"Alpaca API Error: {str(e)}")],
                "node_latencies_ms": {"execution_agent_node": timer.elapsed_ms},
            }
