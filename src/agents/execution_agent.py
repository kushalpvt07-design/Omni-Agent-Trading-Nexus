import os
import json
from langchain_core.messages import AIMessage
from src.state import FinancialSwarmState

# A simple file-based ledger to simulate a live brokerage portfolio balance
LEDGER_FILE = "portfolio_ledger.json"

def load_ledger():
    if not os.path.exists(LEDGER_FILE):
        # Initialize with $100,000 cash and an empty positions list
        initial_ledger = {"cash": 100000.0, "positions": {}}
        with open(LEDGER_FILE, "w") as f:
            json.dump(initial_ledger, f, indent=4)
        return initial_ledger
    with open(LEDGER_FILE, "r") as f:
        return json.load(f)

def save_ledger(ledger):
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=4)

async def execution_agent_node(state: FinancialSwarmState) -> dict:
    """
    The Execution Agent. Simulates order routing to a brokerage,
    calculates cash balances, and updates the local ledger.
    """
    trade = state.get("proposed_trade", {})
    ticker = trade.get("ticker")
    action = trade.get("action")
    shares = trade.get("shares", 0)
    
    # If the orchestrator decided to HOLD, wrap it up immediately
    if not action or action == "HOLD" or shares <= 0:
        return {"messages": [AIMessage(content="Execution Engine: No action taken. Pipeline finished with HOLD status.")]}
    
    # In production, this mock price would come from a real-time WebSocket feed
    mock_market_price = 150.0 
    total_cost = mock_market_price * shares
    
    print(f"\n⚡ Execution Engine: Routing {action} order for {shares} shares of {ticker} to market...")
    
    ledger = load_ledger()
    
    if action == "BUY":
        if ledger["cash"] < total_cost:
            error_msg = f"TRADE REJECTED: Insufficient funds. Required: ${total_cost:.2f}, Available: ${ledger['cash']:.2f}"
            print(f"❌ {error_msg}")
            return {"errors": [error_msg]}
        
        # Deduct cash and update position
        ledger["cash"] -= total_cost
        ledger["positions"][ticker] = ledger["positions"].get(ticker, 0) + shares
        
    elif action == "SELL":
        current_shares = ledger["positions"].get(ticker, 0)
        if current_shares < shares:
            error_msg = f"TRADE REJECTED: Insufficient shares. Trying to sell {shares}, but only own {current_shares}."
            print(f"❌ {error_msg}")
            return {"errors": [error_msg]}
        
        # Add cash and reduce position
        ledger["cash"] += total_cost
        ledger["positions"][ticker] -= shares
        if ledger["positions"][ticker] == 0:
            del ledger["positions"][ticker]

    save_ledger(ledger)
    
    execution_report = (
        f"✅ **Brokerage Order Executed Successfully!**\n"
        f"**Filled:** {action} {shares} shares of {ticker} @ ${mock_market_price:.2f}\n"
        f"**Total Transaction Value:** ${total_cost:.2f}\n"
        f"**Remaining Cash Portfolio Balance:** ${ledger['cash']:.2f}"
    )
    
    return {"messages": [AIMessage(content=execution_report)]}
