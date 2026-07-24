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
    
    if action in ["HOLD", "REJECT"] or live_price <= 0:
        return {"messages": ["Execution Engine: No action taken. Holding position."]}

    # GUARD: Alpaca does not support non-US regional symbols (e.g. .NS, .BO)
    if "." in ticker:
        return {
            "messages": [f"Execution Engine: Skipping Alpaca submission for regional stock '{ticker}'. Alpaca only supports US equities and selected cryptos."]
        }

    cash_available = get_available_cash()

    # FIX: Use explicit share count if defined by user/LLM; otherwise derive from allocation
    proposed_shares = float(trade.get("shares", 0.0))
    if proposed_shares > 0.0:
        shares = proposed_shares
    elif action == "BUY" and allocation > 0:
        shares = round((cash_available * allocation) / live_price, 4)
    elif action == "SELL":
        # For SELL orders without explicit shares, require explicit share count or handle broker position sizing
        return {"messages": ["Execution Engine: Sell order requires explicit share quantity."]}
    else:
        return {"messages": ["Execution Engine: No shares or allocation specified. Action cancelled."]}

    trade["shares"] = shares
    
    is_paper = state.get("paper_trading_enabled", True)
    asset_class = state.get("asset_class", "equity")
    
    client = TradingClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), paper=is_paper)
    
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
        return {
            "proposed_trade": trade,
            "messages": [f"Order executed ({mode}): {action} {shares} shares of {ticker}. Alpaca Order ID: {order.id}"]
        }
    except Exception as e:
        return {"errors": [f"Alpaca API Error: {str(e)}"]}
