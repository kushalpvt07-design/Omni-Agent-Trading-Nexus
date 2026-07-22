import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from src.agents.risk_agent import get_available_cash

def execution_agent_node(state):
    # Stop if Risk Desk vetoed the trade
    if not state.get("risk_approved", False):
        return {"messages": ["Execution skipped: Risk Desk rejected the trade."]}
    
    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")
    ticker = trade.get("ticker", "")
    allocation = trade.get("allocation", 0.0)
    live_price = trade.get("estimated_price", 0.0)
    
    if action == "HOLD" or allocation <= 0 or live_price <= 0:
        return {"messages": ["Execution Engine: No action taken. Holding position."]}
        
    cash_available = get_available_cash()
    # Natively calculate fractional shares (round to 4 decimal places for fractional support)
    shares = round((cash_available * allocation) / live_price, 4)
    trade["shares"] = shares
    
    is_paper = state.get("paper_trading_enabled", True)
    
    # Initialize Alpaca Client (paper=True for simulation, False for live capital)
    client = TradingClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), paper=is_paper)
    
    # Build the order payload
    order_data = MarketOrderRequest(
        symbol=ticker,
        qty=shares,
        side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    
    try:
        # Fire the actual API request to the broker
        order = client.submit_order(order_data)
        mode = "PAPER" if is_paper else "LIVE"
        return {
            "proposed_trade": trade,
            "messages": [f"Order executed ({mode}): {action} {shares} shares of {ticker}. Alpaca Order ID: {order.id}"]
        }
    except Exception as e:
        # Catch broker errors (e.g., insufficient buying power, invalid ticker)
        return {"errors": [f"Alpaca API Error: {str(e)}"]}
