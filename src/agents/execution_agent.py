import os
import json
import asyncio
import logging
from langchain_core.messages import AIMessage
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from src.state import FinancialSwarmState
from src.agents.risk_agent import get_ledger_data, save_ledger_data, LEDGER_FILE

logger = logging.getLogger("omni-nexus.execution")


async def execution_agent_node(state: FinancialSwarmState) -> dict:
    if not state.get("risk_approved", False):
        return {"messages": [AIMessage(content="Execution skipped: Risk Desk rejected the trade.")]}

    if state.get("requires_human_approval", True) and not state.get("human_approved", False):
        return {"messages": [AIMessage(content="Execution stalled: Waiting for explicit human approval.")]}

    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")
    ticker = trade.get("ticker", "")
    live_price = trade.get("estimated_price", 0.0)

    if action in ["HOLD", "REJECT"] or live_price <= 0:
        return {"messages": [AIMessage(content="Execution Engine: No action taken. Holding position.")]}

    if "." in ticker:
        return {
            "messages": [AIMessage(content=f"Execution Engine: Skipping Alpaca submission for international stock '{ticker}'.")]
        }

    # Trust the Risk Desk's precise share calculation
    raw_shares = trade.get("shares")
    shares = float(raw_shares) if raw_shares is not None else 0.0

    if shares <= 0:
        return {
            "errors": ["Execution Engine: Share quantity is 0 or invalid. Trade aborted."],
            "messages": [AIMessage(content="Execution Engine aborted: Share quantity is 0.")],
        }

    trade["shares"] = shares
    is_paper = state.get("paper_trading_enabled", True)
    asset_class = state.get("asset_class", "equity")

    api_key = os.getenv("ALPACA_API_KEY")
    sec_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not sec_key:
        return {
            "errors": ["Execution Engine: Missing Alpaca API credentials."],
            "messages": [AIMessage(content="Execution Engine aborted: Missing API credentials.")],
        }

    client = TradingClient(api_key, sec_key, paper=is_paper)
    tif = TimeInForce.GTC if asset_class == "crypto" else TimeInForce.DAY

    order_data = MarketOrderRequest(
        symbol=ticker,
        qty=shares,
        side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
        time_in_force=tif,
    )

    try:
        # Run synchronous Alpaca SDK call off the event loop
        order = await asyncio.to_thread(client.submit_order, order_data)
        mode = "PAPER" if is_paper else "LIVE"

        # Update ledger with file-safe write
        ledger = get_ledger_data()

        trade_value = shares * live_price
        if action == "BUY":
            ledger["cash"] -= trade_value
            ledger["positions"][ticker] = ledger["positions"].get(ticker, 0.0) + shares
        elif action == "SELL":
            ledger["cash"] += trade_value
            ledger["positions"][ticker] = ledger["positions"].get(ticker, 0.0) - shares
            if round(ledger["positions"][ticker], 4) <= 0:
                del ledger["positions"][ticker]

        save_ledger_data(ledger)

        logger.info(
            "Order executed (%s): %s %s shares of %s — Alpaca ID: %s",
            mode, action, shares, ticker, order.id,
        )

        return {
            "proposed_trade": trade,
            "messages": [AIMessage(content=f"Order executed ({mode}): {action} {shares} shares of {ticker}. Alpaca Order ID: {order.id}. Ledger Updated.")],
        }
    except Exception as e:
        logger.exception("Alpaca API Error for %s %s %s", action, shares, ticker)
        return {
            "errors": [f"Alpaca API Error: {str(e)}"],
            "messages": [AIMessage(content=f"Alpaca API Error: {str(e)}")],
        }
