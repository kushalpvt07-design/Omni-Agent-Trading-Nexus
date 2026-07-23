import os
import json
import re
from dotenv import load_dotenv

load_dotenv()
if "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from schemas import TradeRequest, TradeResponse
from langchain_core.messages import HumanMessage
from swarm import app as trading_swarm 

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Omni-Agent Trading Nexus API",
    description="Backend engine for the autonomous trading swarm.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            return TradeResponse(
                status="ERROR",
                error_message=error_details
            )
            
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

def sanitize_raw_input(raw_text: str) -> str:
    if not raw_text:
        return ""
    
    # Strip null bytes and non-printable characters
    clean_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw_text)
    
    # Collapse multiple spaces and newlines
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Truncate absurdly long inputs to prevent token-stuffing attacks
    return clean_text[:500] 

@app.websocket("/api/v1/swarm-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                data = await websocket.receive_text()
                payload = json.loads(data)
                raw_directive = payload.get("directive", "")
                paper_trading = payload.get("paper_trading", True)
                
                directive = sanitize_raw_input(raw_directive)
                
                if not directive:
                    await websocket.send_json({
                        "type": "message",
                        "role": "System Alert",
                        "content": "Received empty or entirely invalid directive. Ignored."
                    })
                    continue
                
                initial_state = {
                    "messages": [HumanMessage(content=directive)],
                    "paper_trading_enabled": paper_trading,
                    "quant_data": {}, 
                    "sentiment_data": {}, 
                    "current_ticker": "", 
                    "proposed_trade": {},
                    "risk_approved": False, 
                    "errors": []
                }
                
                # Stream events
                async for event in trading_swarm.astream(initial_state, stream_mode="updates"):
                    for node_name, node_state in event.items():
                        if not isinstance(node_state, dict):
                            continue
                            
                        # Check for messages to display
                        messages = node_state.get("messages", [])
                        if messages:
                            last_message = messages[-1]
                            content = getattr(last_message, "content", str(last_message))
                            await websocket.send_json({
                                "type": "message",
                                "role": node_name.replace("_agent_node", "").replace("_node", "").capitalize(),
                                "content": content
                            })
                        else:
                            await websocket.send_json({
                                "type": "message",
                                "role": node_name.replace("_agent_node", "").replace("_node", "").capitalize(),
                                "content": f"Processing update..."
                            })
                        
                        # If there's an error, send it
                        if node_state.get("errors"):
                            await websocket.send_json({
                                "type": "message",
                                "role": f"System Alert",
                                "content": " | ".join(node_state["errors"])
                            })
                            
                # Final result notification
                await websocket.send_json({
                    "type": "message",
                    "role": "System",
                    "content": "Swarm pipeline execution completed."
                })
            except Exception as e:
                await websocket.send_json({"type": "message", "role": "System Error", "content": str(e)})
            
    except WebSocketDisconnect:
        print("Client disconnected from Swarm stream")
