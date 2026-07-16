import os
import json
from langchain_core.messages import AIMessage
from src.state import FinancialSwarmState
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

LEDGER_FILE = "portfolio_ledger.json"

# -- Local Ledger Functions (Unchanged) --
def load_ledger():
    if not os.path.exists(LEDGER_FILE):
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
    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")
    shares = trade.get("shares", 0)
    ticker = trade.get("ticker", "UNKNOWN")
    
    # NEW: Check if the UI toggled Paper Trading on
    is_paper_trading = state.get("paper_trading_enabled", False)

    if action == "HOLD" or shares <= 0:
        return {"messages": [AIMessage(content="Execution Engine: No action taken. Pipeline finished with HOLD status.")]}
    
    # ---------------------------------------------------------
    # ROUTE A: LIVE PAPER TRADING (ALPACA)
    # ---------------------------------------------------------
    if is_paper_trading:
        try:
            api_key = os.environ.get("ALPACA_API_KEY")
            secret_key = os.environ.get("ALPACA_SECRET_KEY")
            
            if not api_key or not secret_key:
                return {"errors": ["Alpaca keys missing from .env file."]}

            # Initialize the modern Trading Client
            trading_client = TradingClient(api_key, secret_key, paper=True)
            
            # Format the order request
            market_order_data = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            
            # Submit the order to the live market
            order = trading_client.submit_order(order_data=market_order_data)
            
            report = (
                f"📈 **ALPACA LIVE EXECUTION SUCCESS**\n"
                f"**Order ID:** {order.id}\n"
                f"**Filled:** {action} {shares} shares of {ticker} on the live order book."
            )
            return {"messages": [AIMessage(content=report)]}
            
        except Exception as e:
            return {"errors": [f"Alpaca Execution Failed: {str(e)}"]}

    # ---------------------------------------------------------
    # ROUTE B: LOCAL MOCK LEDGER
    # ---------------------------------------------------------
    else:
        mock_market_price = 150.0 
        total_cost = mock_market_price * shares
        ledger = load_ledger()
        
        if action == "BUY":
            if ledger["cash"] < total_cost:
                return {"errors": [f"Insufficient funds. Required: ${total_cost:.2f}"]}
            ledger["cash"] -= total_cost
            ledger["positions"][ticker] = ledger["positions"].get(ticker, 0) + shares
            
        elif action == "SELL":
            if ledger["positions"].get(ticker, 0) < shares:
                return {"errors": ["Insufficient shares."]}
            ledger["cash"] += total_cost
            ledger["positions"][ticker] -= shares
            if ledger["positions"][ticker] == 0:
                del ledger["positions"][ticker]

        save_ledger(ledger)
        report = (
            f"✅ **LOCAL LEDGER EXECUTED**\n"
            f"**Filled:** {action} {shares} shares of {ticker} @ ${mock_market_price:.2f}\n"
            f"**Remaining Cash:** ${ledger['cash']:.2f}"
        )
        return {"messages": [AIMessage(content=report)]}
