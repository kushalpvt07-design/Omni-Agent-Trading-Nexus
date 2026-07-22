import os
import json
from langchain_core.messages import AIMessage
from src.state import FinancialSwarmState

LEDGER_FILE = "portfolio_ledger.json"

def get_available_cash():
    """Reads the ledger to see how much money you haven't lost yet."""
    if not os.path.exists(LEDGER_FILE):
        return 100000.0 # Default starting cash
    try:
        with open(LEDGER_FILE, "r") as f:
            return json.load(f).get("cash", 100000.0)
    except Exception:
        return 0.0 # If the file is locked or corrupted, assume zero cash to freeze trading

async def pre_flight_risk_node(state: FinancialSwarmState) -> dict:
    """Short-circuits the pipeline if portfolio cash is insufficient."""
    cash_available = get_available_cash()
    if cash_available < 100.0:
        return {"errors": ["PRE_FLIGHT_REJECTION: Insufficient funds in ledger to execute any trade. Aborting pipeline."]}
    return {}

async def risk_agent_node(state: FinancialSwarmState) -> dict:
    """
    The Risk Desk. Intercepts the Orchestrator's proposal and runs compliance checks.
    If the trade violates risk parameters, it forcefully overrides the state.
    """
    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")
    allocation = trade.get("allocation", 0.0)
    ticker = trade.get("ticker", "UNKNOWN")

    # Pass-through if no action is required
    if action == "HOLD" or allocation <= 0:
        return {
            "risk_approved": True, 
            "messages": [AIMessage(content="🛡️ Risk Desk: No active trade proposed. Cleared.")]
        }

    # Pull live price and metrics from Quant memory.
    quant_data = state.get("quant_data", {}).get(ticker, "")
    live_price = 150.0
    std_dev = 0.0
    if quant_data:
        try:
            parsed_quant = json.loads(quant_data)
            if "latest_close" in parsed_quant:
                live_price = float(parsed_quant["latest_close"])
            metrics = parsed_quant.get("volatility_metrics", {})
            if "30_day_standard_deviation" in metrics:
                std_dev = float(metrics["30_day_standard_deviation"])
        except Exception:
            pass
            
    cash_available = get_available_cash()
    requested_trade_value = cash_available * allocation

    # Dynamic Position Sizing based on volatility
    volatility_pct = (std_dev / live_price) if live_price > 0 else 0
    # Base allocation 30%, reduce aggressively for high volatility, minimum 5%
    allocation_pct = max(0.05, 0.30 - (volatility_pct * 2.0))
    max_allowed_spend = cash_available * allocation_pct

    print(f"\n[Risk Desk] analyzing {action} order for {allocation*100:.1f}% allocation of {ticker} (Requested: ${requested_trade_value:,.2f} | Max allowed: ${max_allowed_spend:,.2f})...")

    if action == "BUY" and allocation > allocation_pct:
        reject_msg = (
            f"⛔ RISK DESK REJECTION: Requested allocation ({allocation*100:.1f}%) exceeds the dynamically adjusted "
            f"maximum limit ({allocation_pct*100:.1f}%). Overriding to HOLD."
        )
        
        original_reasoning = trade.get("reasoning", "No original reasoning provided.")
        
        # Forcefully overwrite the Orchestrator's trade with a dead HOLD order
        overridden_trade = {
            "ticker": ticker,
            "action": "HOLD",
            "allocation": 0.0,
            "shares": 0,
            "estimated_price": live_price,
            "reasoning": f"[RISK REJECTION: Exceeds dynamically adjusted cash limit] Original LLM Analysis: {original_reasoning}"
        }
        
        return {
            "risk_approved": False, 
            "proposed_trade": overridden_trade, 
            "messages": [AIMessage(content=reject_msg)]
        }

    approve_msg = f"✅ RISK DESK APPROVAL: Allocation ({allocation*100:.1f}%) is within compliance limits. Routing to Human Checkpoint."

    # Update trade with live price so execution agent doesn't have to pull it again
    updated_trade = trade.copy()
    updated_trade["estimated_price"] = live_price

    return {
        "risk_approved": True, 
        "proposed_trade": updated_trade,
        "messages": [AIMessage(content=approve_msg)]
    }
