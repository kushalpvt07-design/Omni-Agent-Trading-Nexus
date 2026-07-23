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
from swarm import build_graph # Import the blueprint, not the compiled app
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
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

def sanitize_raw_input(raw_text: str) -> str:
    if not raw_text:
        return ""
    clean_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text[:500] 

# Stateless POST endpoint for your Streamlit toy UI
@app.post("/api/v1/analyze", response_model=TradeResponse)
async def analyze_trade(request: TradeRequest):
    try:
        # Compile on the fly without a checkpointer for the stateless REST call
        stateless_swarm = build_graph().compile()
        
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
        final_state = await stateless_swarm.ainvoke(initial_state)
        
        if final_state.get("errors"):
            return TradeResponse(status="ERROR", error_message=" | ".join(final_state["errors"]))
            
        proposed_trade = final_state.get("proposed_trade", {})
        ticker = proposed_trade.get("ticker") or final_state.get("current_ticker") or "UNKNOWN"
        
        return TradeResponse(
            status="success",
            ticker=ticker,
            action=proposed_trade.get("action", "HOLD"),
            shares=proposed_trade.get("shares", 0),
            risk_approved=final_state.get("risk_approved", False),
            orchestrator_reasoning=proposed_trade.get("reasoning", "No reasoning provided.")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Swarm execution failed: {str(e)}")


# Stateful WebSocket for your actual React Dashboard
@app.websocket("/api/v1/swarm-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # You MUST use a checkpointer to persist the thread state while waiting for approval
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        
        # Compile WITH the human interrupt
        trading_swarm = build_graph().compile(
            checkpointer=checkpointer,
            interrupt_before=["execution_agent"]
        )
        
        session_id = f"session_{id(websocket)}"
        config = {"configurable": {"thread_id": session_id}}

        try:
            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                
                # ---------------------------------------------------------
                # INTERCEPT: Did the frontend just send an approval action?
                # ---------------------------------------------------------
                if payload.get("type") == "human_approval":
                    is_approved = payload.get("approved", False)
                    
                    if is_approved:
                        await websocket.send_json({"type": "message", "role": "System", "content": "Trade Approved. Dispatching to Execution Agent..."})
                        
                        # Resume the graph from the exact point it paused by passing None
                        async for event in trading_swarm.astream(None, config=config, stream_mode="updates"):
                            for node_name, node_state in event.items():
                                messages = node_state.get("messages", [])
                                if messages:
                                    content = getattr(messages[-1], "content", str(messages[-1]))
                                    await websocket.send_json({"type": "message", "role": "Execution Hub", "content": content})
                    else:
                        await websocket.send_json({"type": "message", "role": "System Alert", "content": "Trade Rejected by User. Swarm halted."})
                    
                    await websocket.send_json({"type": "message", "role": "System", "content": "Transaction cycle closed."})
                    continue

                # ---------------------------------------------------------
                # STANDARD EXECUTION: Process a new directive
                # ---------------------------------------------------------
                raw_directive = payload.get("directive", "")
                directive = sanitize_raw_input(raw_directive)
                
                if not directive:
                    continue
                
                initial_state = {
                    "messages": [HumanMessage(content=directive)],
                    "paper_trading_enabled": payload.get("paper_trading", True),
                    "quant_data": {}, 
                    "sentiment_data": {}, 
                    "current_ticker": "", 
                    "proposed_trade": {},
                    "risk_approved": False, 
                    "errors": []
                }
                
                # Stream events normally up until the interrupt barrier
                async for event in trading_swarm.astream(initial_state, config=config, stream_mode="updates"):
                    for node_name, node_state in event.items():
                        if not isinstance(node_state, dict):
                            continue
                            
                        messages = node_state.get("messages", [])
                        if messages:
                            content = getattr(messages[-1], "content", str(messages[-1]))
                            
                            # Determine role based on which agent just finished
                            role_map = {
                                "parser_agent": "Parser",
                                "sentiment_agent": "Sentiment",
                                "quant_agent": "Quant",
                                "orchestrator": "Orchestrator",
                                "risk_agent": "Risk"
                            }
                            role_name = role_map.get(node_name, node_name.capitalize())
                            
                            await websocket.send_json({
                                "type": "message",
                                "role": role_name,
                                "content": content
                            })
                            
                        # INJECT MOCK OHLC DATA ONCE PARSER IS DONE
                        if node_name == "parser_agent" and node_state.get("current_ticker"):
                            import random
                            ticker = node_state["current_ticker"]
                            base_price = 150.0 if "USD" not in ticker else 60000.0
                            chart_data = []
                            for i in range(30):
                                open_p = base_price + random.uniform(-3, 3)
                                close_p = open_p + random.uniform(-2, 2)
                                chart_data.append({
                                    "date": f"Day {i+1}",
                                    "open": open_p,
                                    "high": max(open_p, close_p) + random.uniform(0, 1),
                                    "low": min(open_p, close_p) - random.uniform(0, 1),
                                    "close": close_p
                                })
                                base_price = close_p
                            await websocket.send_json({
                                "type": "chart_data",
                                "ticker": ticker,
                                "data": chart_data
                            })
                        
                        if node_state.get("errors"):
                            await websocket.send_json({
                                "type": "message",
                                "role": "System Alert",
                                "content": " | ".join(node_state["errors"])
                            })
                            
                # CRITICAL: Inspect the graph state to see if it paused at the execution gate
                current_state = await trading_swarm.aget_state(config)
                if current_state.next and "execution_agent" in current_state.next:
                    proposed_trade = current_state.values.get("proposed_trade", {})
                    # Blast this event to Next.js so the React state updates and unhides the Approve/Reject buttons
                    await websocket.send_json({
                        "type": "checkpoint",
                        "role": "System",
                        "content": "Awaiting human authorization to execute live trade.",
                        "trade_details": {
                            "ticker": proposed_trade.get("ticker", "UNKNOWN"),
                            "action": proposed_trade.get("action", "REVIEW"),
                            "allocation": float(proposed_trade.get("allocation", 0)) * 100,
                            "shares": float(proposed_trade.get("shares", 0))
                        }
                    })
                else:
                    await websocket.send_json({
                        "type": "message",
                        "role": "System",
                        "content": "Swarm pipeline execution finished or aborted by Risk Desk."
                    })
                    
        except WebSocketDisconnect:
            print(f"Client disconnected from Swarm stream: {session_id}")
