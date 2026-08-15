import os
import json
import logging
import tempfile
from langchain_core.messages import AIMessage
from src.state import FinancialSwarmState

logger = logging.getLogger("omni-nexus.risk")

LEDGER_FILE = "portfolio_ledger.json"


def get_ledger_data() -> dict:
    """Reads the portfolio ledger. Returns safe defaults if the file is missing or corrupt."""
    if not os.path.exists(LEDGER_FILE):
        return {"cash": 100000.0, "positions": {}}
    try:
        with open(LEDGER_FILE, "r") as f:
            data = json.load(f)
            return {
                "cash": data.get("cash", 100000.0),
                "positions": data.get("positions", {}),
            }
    except Exception:
        logger.warning("Ledger file is corrupt or unreadable — returning empty ledger")
        return {"cash": 0.0, "positions": {}}


def save_ledger_data(ledger: dict) -> None:
    """Atomically writes the ledger via temp-file + rename to prevent corruption."""
    dir_name = os.path.dirname(os.path.abspath(LEDGER_FILE))
    fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=dir_name)
    try:
        with os.fdopen(fd, "w") as tmp_f:
            json.dump(ledger, tmp_f, indent=4)
        os.replace(tmp_path, LEDGER_FILE)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def get_available_cash() -> float:
    return get_ledger_data()["cash"]


async def risk_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {"risk_approved": False}

    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")

    raw_shares = trade.get("shares")
    shares = float(raw_shares) if raw_shares is not None else 0.0

    raw_alloc = trade.get("allocation")
    allocation = float(raw_alloc) if raw_alloc is not None else 0.0

    ticker = state.get("current_ticker", "UNKNOWN")

    if action in ["HOLD", "REJECT"]:
        return {
            "risk_approved": True,
            "messages": [AIMessage(content=f"🛡️ Risk Desk: Acknowledged orchestration directive to {action}.")],
        }

    quant_data = state.get("quant_data", {}).get(ticker, "")
    live_price = 0.0
    std_dev = 0.0

    if quant_data:
        try:
            parsed_quant = json.loads(quant_data)
            live_price = float(parsed_quant.get("latest_close", 0.0))
            std_dev = float(
                parsed_quant.get("volatility_metrics", {}).get(
                    "30_day_standard_deviation", 0.0
                )
            )
        except Exception:
            pass

    if live_price <= 0.0:
        return {
            "risk_approved": False,
            "errors": [f"FATAL: Risk Desk could not resolve live price for {ticker}. Aborting."],
        }

    ledger = get_ledger_data()
    cash_available = ledger["cash"]
    positions = ledger["positions"]

    if action == "SELL":
        owned_shares = float(positions.get(ticker, 0.0))
        if owned_shares <= 0.0:
            reject_msg = f"⛔ RISK DESK REJECTION: Attempted to SELL {ticker}, but ledger shows 0 shares owned. Naked shorting is prohibited. Overriding to HOLD."
            overridden_trade = {
                **trade,
                "action": "HOLD",
                "allocation": 0.0,
                "shares": 0.0,
                "estimated_price": live_price,
                "reasoning": f"[RISK REJECTION: Naked shorting prohibited] {trade.get('reasoning', '')}",
            }
            return {
                "risk_approved": False,
                "proposed_trade": overridden_trade,
                "messages": [AIMessage(content=reject_msg)],
            }

        # Respect allocation parameters for partial exits
        if shares <= 0.0 and allocation > 0:
            sell_shares = owned_shares * allocation
        else:
            sell_shares = shares if shares > 0 else owned_shares

        if sell_shares > owned_shares:
            reject_msg = f"⛔ RISK DESK REJECTION: Attempted to SELL {sell_shares} of {ticker}, but ledger only shows {owned_shares} shares owned. Overriding to HOLD."
            overridden_trade = {
                **trade,
                "action": "HOLD",
                "allocation": 0.0,
                "shares": 0.0,
                "estimated_price": live_price,
                "reasoning": f"[RISK REJECTION: Insufficient shares for sell order] {trade.get('reasoning', '')}",
            }
            return {
                "risk_approved": False,
                "proposed_trade": overridden_trade,
                "messages": [AIMessage(content=reject_msg)],
            }

        approve_msg = f"✅ RISK DESK APPROVAL: Valid SELL order for {ticker}. Inventory verified. Routing to Human Checkpoint."
        updated_trade = trade.copy()
        updated_trade["estimated_price"] = live_price
        updated_trade["shares"] = sell_shares

        return {
            "risk_approved": True,
            "proposed_trade": updated_trade,
            "messages": [AIMessage(content=approve_msg)],
        }

    # ── BUY LOGIC ───────────────────────────────────────────────
    if shares > 0:
        requested_trade_value = shares * live_price
        actual_allocation = requested_trade_value / cash_available if cash_available > 0 else 1.0
    else:
        actual_allocation = allocation if allocation > 0 else 0.1
        requested_trade_value = cash_available * actual_allocation

    # Overdraft guard
    if action == "BUY" and requested_trade_value > cash_available:
        reject_msg = f"⛔ RISK DESK REJECTION: Requested trade value (${requested_trade_value:,.2f}) exceeds total available cash (${cash_available:,.2f}). Overriding to HOLD."
        overridden_trade = {
            **trade,
            "action": "HOLD",
            "allocation": 0.0,
            "shares": 0.0,
            "estimated_price": live_price,
            "reasoning": "[RISK REJECTION: Insufficient Cash]",
        }
        return {
            "risk_approved": False,
            "proposed_trade": overridden_trade,
            "messages": [AIMessage(content=reject_msg)],
        }

    volatility_pct = (std_dev / live_price) if live_price > 0 else 0
    allocation_pct = max(0.05, 0.30 - (volatility_pct * 2.0))
    max_allowed_spend = cash_available * allocation_pct

    logger.info(
        "Risk analysis for %s %s: allocation=%.1f%% requested=$%,.2f max_allowed=$%,.2f",
        action, ticker, actual_allocation * 100, requested_trade_value, max_allowed_spend,
    )

    if action == "BUY" and actual_allocation > allocation_pct:
        reject_msg = (
            f"⛔ RISK DESK REJECTION: Requested position size (${requested_trade_value:,.2f} / {actual_allocation*100:.1f}%) "
            f"exceeds the dynamically adjusted volatility limit (${max_allowed_spend:,.2f} / {allocation_pct*100:.1f}%). Overriding to HOLD."
        )
        original_reasoning = trade.get("reasoning", "No original reasoning provided.")

        overridden_trade = {
            "ticker": ticker,
            "action": "HOLD",
            "allocation": 0.0,
            "shares": 0.0,
            "estimated_price": live_price,
            "reasoning": f"[RISK REJECTION: Exceeds dynamically adjusted cash limit] Original LLM Analysis: {original_reasoning}",
        }
        return {
            "risk_approved": False,
            "proposed_trade": overridden_trade,
            "messages": [AIMessage(content=reject_msg)],
        }

    approve_msg = f"✅ RISK DESK APPROVAL: Trade size (${requested_trade_value:,.2f}) is within compliance limits. Routing to Human Checkpoint."

    updated_trade = trade.copy()
    updated_trade["estimated_price"] = live_price
    updated_trade["allocation"] = actual_allocation

    # Set exact shares for execution agent
    if not updated_trade.get("shares"):
        updated_trade["shares"] = requested_trade_value / live_price

    return {
        "risk_approved": True,
        "proposed_trade": updated_trade,
        "messages": [AIMessage(content=approve_msg)],
    }
