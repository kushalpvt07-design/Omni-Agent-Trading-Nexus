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
    shares = trade.get("shares", 0)
    ticker = trade.get("ticker", "UNKNOWN")

    # Pass-through if no action is required
    if action == "HOLD" or shares <= 0:
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
            
    trade_value = live_price * shares
    cash_available = get_available_cash()

    # Dynamic Position Sizing based on volatility
    volatility_pct = (std_dev / live_price) if live_price > 0 else 0
    # Base allocation 30%, reduce aggressively for high volatility, minimum 5%
    allocation_pct = max(0.05, 0.30 - (volatility_pct * 2.0))
    max_allowed_spend = cash_available * allocation_pct

    print(f"\n[Risk Desk] analyzing {action} order for {shares} shares of {ticker} at ${live_price:,.2f} (Vol: {volatility_pct:.1%} -> Max Allocation: {allocation_pct:.1%})...")

    if action == "BUY" and trade_value > max_allowed_spend:
        reject_msg = (
            f"⛔ RISK DESK REJECTION: Trade value (${trade_value:,.2f}) exceeds the dynamically adjusted "
            f"{allocation_pct:.1%} maximum cash allocation limit (${max_allowed_spend:,.2f}). Overriding to HOLD."
        )
        
        original_reasoning = trade.get("reasoning", "No original reasoning provided.")
        
        # Forcefully overwrite the Orchestrator's trade with a dead HOLD order
        overridden_trade = {
            "ticker": ticker,
            "action": "HOLD",
            "shares": 0,
            "estimated_price": live_price,
            "reasoning": f"[RISK REJECTION: Exceeds dynamically adjusted cash limit] Original LLM Analysis: {original_reasoning}"
        }
        
        return {
            "risk_approved": False, 
            "proposed_trade": overridden_trade, 
            "messages": [AIMessage(content=reject_msg)]
        }

    approve_msg = f"✅ RISK DESK APPROVAL: Trade value (${trade_value:,.2f}) is within compliance limits. Routing to Human Checkpoint."

    return {
        "risk_approved": True, 
        "messages": [AIMessage(content=approve_msg)]
    }
