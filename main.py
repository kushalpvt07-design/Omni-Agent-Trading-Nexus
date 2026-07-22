import os
from dotenv import load_dotenv

load_dotenv()
if "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

from fastapi import FastAPI, HTTPException
from schemas import TradeRequest, TradeResponse
from langchain_core.messages import HumanMessage
from swarm import app as trading_swarm 

app = FastAPI(
    title="Omni-Agent Trading Nexus API",
    description="Backend engine for the autonomous trading swarm.",
    version="1.0.0"
)

@app.post("/api/v1/analyze", response_model=TradeResponse)
async def analyze_trade(request: TradeRequest):
    try:
        # 1. Initialize the pristine state for the swarm
        initial_state = {
            "messages": [HumanMessage(content=request.directive)],
            "paper_trading_enabled": request.paper_trading,
            "quant_data": {}, 
            "sentiment_data": {}, 
            "current_ticker": "", 
            "proposed_trade": {},
            "risk_approved": False, 
            "errors": []
        }
        
        # 2. Asynchronously invoke the Swarm
        final_state = await trading_swarm.ainvoke(initial_state)
        
        # 3. Extract the critical data from the Swarm's final state
        if final_state.get("errors"):
            error_details = " | ".join(final_state["errors"])
            raise HTTPException(status_code=400, detail=f"Swarm encountered errors: {error_details}")
            
        proposed_trade = final_state.get("proposed_trade", {})
        
        # Safely extract the ticker, falling back to current_ticker, or UNKNOWN
        ticker = proposed_trade.get("ticker") or final_state.get("current_ticker") or "UNKNOWN"
        
        return TradeResponse(
            status="success",
            ticker=ticker,
            action=proposed_trade.get("action", "HOLD"),
            shares=proposed_trade.get("shares", 0),
            risk_approved=final_state.get("risk_approved", False),
            orchestrator_reasoning=proposed_trade.get("reasoning", "No reasoning provided.")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Don't just fail silently like a junior dev. Catch and raise proper HTTP errors.
        raise HTTPException(status_code=500, detail=f"Swarm execution failed: {str(e)}")

# Health check endpoint so you know your server hasn't died
@app.get("/health")
def health_check():
    return {"status": "operational", "system": "Omni-Agent Nexus"}
