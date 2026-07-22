import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

def execution_agent_node(state):
    # Stop if Risk Desk vetoed the trade
    if not state.get("risk_approved", False):
        return {"messages": ["Execution skipped: Risk Desk rejected the trade."]}
    
    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")
    ticker = trade.get("ticker", "")
    shares = trade.get("shares", 0)
    
    if action == "HOLD" or shares <= 0:
        return {"messages": ["Execution Engine: No action taken. Holding position."]}
        
    is_paper = state.get("paper_trading_enabled", True)
    
    # Initialize Alpaca Client (paper=True for simulation, False for live capital)
    client = TradingClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), paper=is_paper)
    
    # Build the order payload
    order_data = MarketOrderRequest(
        symbol=ticker,
        qty=shares,
        side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
        time_in_force=TimeInForce.GTC
    )
    
    try:
        # Fire the actual API request to the broker
        order = client.submit_order(order_data)
        mode = "PAPER" if is_paper else "LIVE"
        return {"messages": [f"Order executed ({mode}): {action} {shares} shares of {ticker}. Alpaca Order ID: {order.id}"]}
    except Exception as e:
        # Catch broker errors (e.g., insufficient buying power, invalid ticker)
        return {"errors": [f"Alpaca API Error: {str(e)}"]}
