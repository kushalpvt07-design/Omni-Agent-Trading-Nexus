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
from swarm import build_graph 
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from fastapi.middleware.cors import CORSMiddleware
from utils import get_live_asset_data

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

@app.post("/api/v1/analyze", response_model=TradeResponse)
async def analyze_trade(request: TradeRequest):
    try:
        stateless_swarm = build_graph().compile()
        
        initial_state = {
            "messages": [HumanMessage(content=request.directive)],
            "paper_trading_enabled": request.paper_trading,
            "quant_data": {}, 
            "sentiment_data": {}, 
            "current_ticker": "", 
            "asset_class": "equity", # FIX: Explicitly initialize
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

@app.websocket("/api/v1/swarm-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
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
                
                if payload.get("type") == "human_approval":
                    is_approved = payload.get("approved", False)
                    
                    if is_approved:
                        await websocket.send_json({"type": "message", "role": "System", "content": "Trade Approved. Dispatching to Execution Agent..."})
                    else:
                        await websocket.send_json({"type": "message", "role": "System Alert", "content": "Trade Rejected by User. Swarm halted."})
                        # FIX: Update state so the execution agent respects the human veto
                        await trading_swarm.aupdate_state(config, {"risk_approved": False})
                    
                    # FIX: Resume graph execution regardless of choice to clear the checkpoint
                    async for event in trading_swarm.astream(None, config=config, stream_mode="updates"):
                        for node_name, node_state in event.items():
                            messages = node_state.get("messages", [])
                            if messages:
                                content = getattr(messages[-1], "content", str(messages[-1]))
                                await websocket.send_json({"type": "message", "role": "Execution Hub", "content": content})
                    
                    await websocket.send_json({"type": "message", "role": "System", "content": "Transaction cycle closed."})
                    continue

                raw_directive = payload.get("directive", "").strip()
                if not raw_directive:
                    continue
                
                initial_state = {
                    "messages": [HumanMessage(content=raw_directive)],
                    "paper_trading_enabled": payload.get("paper_trading", True),
                    "quant_data": {},
                    "sentiment_data": {},
                    "current_ticker": "",
                    "asset_class": "equity", # FIX: Explicitly initialize
                    "proposed_trade": {},
                    "risk_approved": False,
                    "errors": []
                }

                PHASE_LABELS = {
                    "parser_node": "Parser Agent: Extracting structured parameters from prompt...",
                    "sentiment_agent": "Sentiment Agent: Scraping news feed & calculating market bias...",
                    "quant_agent": "Quant Agent: Analyzing technical indicators & volatility...",
                    "orchestrator": "Orchestrator Agent: Synthesizing swarm intelligence...",
                    "risk_agent": "Risk Desk: Checking exposure limits & compliance thresholds...",
                    "execution_agent": "Execution Agent: Order execution ready."
                }

                async for event in trading_swarm.astream(initial_state, config=config, stream_mode="updates"):
                    for node_name, node_state in event.items():
                        phase_text = PHASE_LABELS.get(node_name, f"Executing node: {node_name}...")
                        await websocket.send_json({
                            "type": "status",
                            "role": "SYSTEM",
                            "content": f"⚡ [PHASE ENTERED] {phase_text}"
                        })

                        if isinstance(node_state, dict):
                            errors = node_state.get("errors", [])
                            if errors:
                                for err in errors:
                                    await websocket.send_json({
                                        "type": "message",
                                        "role": "SYSTEM ERROR",
                                        "content": f"🚨 {err}"
                                    })
                                    
                            messages = node_state.get("messages", [])
                            if messages:
                                content = getattr(messages[-1], "content", str(messages[-1]))
                                agent_role = node_name.replace("_node", "").replace("_agent", "").upper()
                                
                                await websocket.send_json({
                                    "type": "message",
                                    "role": agent_role,
                                    "content": content
                                })

                        if node_name == "parser_node":
                            extracted_ticker = node_state.get("current_ticker") 
                            if extracted_ticker:
                                live_data = get_live_asset_data(extracted_ticker)
                                if live_data:
                                    await websocket.send_json({
                                        "type": "asset_intelligence",
                                        "data": live_data
                                    })

                current_state = await trading_swarm.aget_state(config)
                if current_state.next and "execution_agent" in current_state.next:
                    proposed_trade = current_state.values.get("proposed_trade", {})
                    await websocket.send_json({
                        "type": "checkpoint",
                        "role": "SYSTEM",
                        "content": "⏸️ Pipeline reached Human-in-the-Loop checkpoint. Awaiting authorization.",
                        "trade_details": {
                            "ticker": proposed_trade.get("ticker", "UNKNOWN"),
                            "action": proposed_trade.get("action", "REVIEW"),
                            "allocation": float(proposed_trade.get("allocation", 0)) * 100,
                            "shares": float(proposed_trade.get("shares", 0))
                        }
                    })
                else:
                    await websocket.send_json({
                        "type": "status",
                        "role": "SYSTEM",
                        "content": "✅ Swarm pipeline execution cycle finished."
                    })

        except (WebSocketDisconnect, RuntimeError):
            print(f"Socket disconnected for session {session_id}")
        except Exception as e:
            print(f"ERROR inside websocket loop: {e}")
