import os
import json
from langchain_core.messages import AIMessage
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from src.agents.risk_agent import get_available_cash, get_ledger_data

def execution_agent_node(state):
    if not state.get("risk_approved", False):
        return {"messages": [AIMessage(content="Execution skipped: Risk Desk rejected the trade.")]}
    
    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")
    ticker = trade.get("ticker", "")
    allocation = trade.get("allocation", 0.0)
    live_price = trade.get("estimated_price", 0.0)
    
    if action in ["HOLD", "REJECT"] or live_price <= 0:
        return {"messages": [AIMessage(content="Execution Engine: No action taken. Holding position.")]}

    if "." in ticker:
        return {
            "messages": [AIMessage(content=f"Execution Engine: Skipping Alpaca submission for regional stock '{ticker}'.")]
        }

    ledger_data = get_ledger_data()
    cash_available = ledger_data["cash"]
    owned_shares = float(ledger_data["positions"].get(ticker, 0.0))

    # SAFE TYPE CAST FIX
    raw_shares = trade.get("shares")
    proposed_shares = float(raw_shares) if raw_shares is not None else 0.0
    
    if proposed_shares > 0.0:
        shares = proposed_shares
    elif action == "BUY" and allocation > 0:
        shares = round((cash_available * allocation) / live_price, 4)
    elif action == "SELL":
        if owned_shares > 0 and allocation > 0:
            shares = round(owned_shares * allocation, 4)
        else:
            return {"messages": [AIMessage(content="Execution Engine: Sell order requires explicit share quantity or valid portfolio inventory.")]}
    else:
        return {"messages": [AIMessage(content="Execution Engine: No shares or allocation specified. Action cancelled.")]}

    # FLAW 3 FIX: Prevent Alpaca 422 HTTP Crash from 0.0 qty orders
    if shares <= 0:
        return {
            "errors": ["Execution Engine: Calculated shares rounded to 0. Trade aborted to prevent API crash."], 
            "messages": [AIMessage(content="Execution Engine aborted: Share quantity is 0.")]
        }

    trade["shares"] = shares
    is_paper = state.get("paper_trading_enabled", True)
    asset_class = state.get("asset_class", "equity")
    
    # FLAW 2 FIX: Validate API credentials before initializing client
    api_key = os.getenv("ALPACA_API_KEY")
    sec_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not sec_key:
        return {
            "errors": ["Execution Engine: Missing Alpaca API credentials in environment."], 
            "messages": [AIMessage(content="Execution Engine aborted: Missing API credentials.")]
        }
        
    client = TradingClient(api_key, sec_key, paper=is_paper)
    tif = TimeInForce.GTC if asset_class == "crypto" else TimeInForce.DAY
    
    order_data = MarketOrderRequest(
        symbol=ticker,
        qty=shares,
        side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
        time_in_force=tif
    )
    
    try:
        order = client.submit_order(order_data)
        mode = "PAPER" if is_paper else "LIVE"
        
        # FLAW 1 FIX: The amnesia-proof ledger update you ignored last time
        ledger_path = "portfolio_ledger.json"
        if os.path.exists(ledger_path):
            with open(ledger_path, "r") as f:
                ledger = json.load(f)
        else:
            ledger = {"cash": 100000.0, "positions": {}}
            
        trade_value = shares * live_price
        if action == "BUY":
            ledger["cash"] -= trade_value
            ledger["positions"][ticker] = ledger["positions"].get(ticker, 0.0) + shares
        elif action == "SELL":
            ledger["cash"] += trade_value
            ledger["positions"][ticker] = ledger["positions"].get(ticker, 0.0) - shares
            # ROUNDING RESIDUAL FIX
            if round(ledger["positions"][ticker], 4) <= 0:
                del ledger["positions"][ticker]
                
        with open(ledger_path, "w") as f:
            json.dump(ledger, f, indent=4)

        return {
            "proposed_trade": trade,
            "messages": [AIMessage(content=f"Order executed ({mode}): {action} {shares} shares of {ticker}. Alpaca Order ID: {order.id}. Ledger Updated.")]
        }
    except Exception as e:
        return {
            "errors": [f"Alpaca API Error: {str(e)}"], 
            "messages": [AIMessage(content=f"Alpaca API Error: {str(e)}")]
        }
