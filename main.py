import os
import json
import re
import uuid
from contextlib import asynccontextmanager
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

global_checkpointer = None
global_stateless_swarm = build_graph().compile()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_checkpointer
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        await checkpointer.setup()
        global_checkpointer = checkpointer
        yield

app = FastAPI(
    title="Omni-Agent Trading Nexus API",
    description="Backend engine for the autonomous trading swarm.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
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
        clean_directive = sanitize_raw_input(request.directive)
        
        initial_state = {
            "messages": [HumanMessage(content=clean_directive)],
            "paper_trading_enabled": request.paper_trading,
            "quant_data": {}, 
            "sentiment_data": {}, 
            "current_ticker": None, 
            "asset_class": "equity",
            "requested_action": None,
            "requested_quantity": None,
            "requested_allocation": None,
            "risk_threshold": 0.5,
            "proposed_trade": {},
            "risk_approved": False, 
            "requires_human_approval": True, # FIX: Added to initialization
            "human_approved": False,         # FIX: Added to initialization
            "errors": []
        }
        
        final_state = await global_stateless_swarm.ainvoke(initial_state)
        
        if final_state.get("errors"):
            return TradeResponse(status="ERROR", error_message=" | ".join(final_state["errors"]))
            
        proposed_trade = final_state.get("proposed_trade")
        if not isinstance(proposed_trade, dict):
            proposed_trade = {}
            
        ticker = proposed_trade.get("ticker") or final_state.get("current_ticker") or "UNKNOWN"
        
        raw_shares = proposed_trade.get("shares")
        try:
            shares_val = float(raw_shares) if raw_shares is not None else None
        except (ValueError, TypeError):
            shares_val = None
            
        return TradeResponse(
            status="success",
            ticker=ticker,
            action=proposed_trade.get("action", "HOLD"),
            shares=shares_val,
            risk_approved=final_state.get("risk_approved", False),
            orchestrator_reasoning=proposed_trade.get("reasoning", "No reasoning provided.")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Swarm execution failed: {str(e)}")

@app.websocket("/api/v1/swarm-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # FIX: Corrected graph mismatch. Now uses standardized _node suffix.
    trading_swarm = build_graph().compile(
        checkpointer=global_checkpointer,
        interrupt_before=["execution_agent_node"]
    )
    
    active_thread_id = None

    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "message", "role": "System Alert", "content": "Invalid transmission received. Ignored."})
                continue
            
            if payload.get("type") == "human_approval":
                if not active_thread_id:
                    await websocket.send_json({"type": "message", "role": "System Alert", "content": "Error: No active trade context."})
                    continue
                    
                config = {"configurable": {"thread_id": active_thread_id}}
                current_state = await trading_swarm.aget_state(config)
                
                # FIX: Corrected graph mismatch logic string here as well.
                if not current_state.next or "execution_agent_node" not in current_state.next:
                    await websocket.send_json({"type": "message", "role": "System Alert", "content": "Error: No active trade pending execution in this thread."})
                    continue

                is_approved = payload.get("approved", False)
                
                if is_approved:
                    await websocket.send_json({"type": "message", "role": "System", "content": "Trade Approved. Dispatching to Execution Agent..."})
                    
                    # FIX: Explicitly update state so execution engine knows it's cleared
                    await trading_swarm.aupdate_state(config, {
                        "human_approved": True
                    })
                else:
                    await websocket.send_json({"type": "message", "role": "System Alert", "content": "Trade Rejected by User. Swarm halted."})
                    
                    raw_trade = current_state.values.get("proposed_trade", {})
                    
                    # FIX: Safely cast to a new dict to avoid AttributeError on frozen state objects
                    safe_trade = dict(raw_trade) if hasattr(raw_trade, "keys") else {}
                        
                    safe_trade["action"] = "HOLD"
                    safe_trade["shares"] = None
                    safe_trade["allocation"] = None
                    safe_trade["ticker"] = "CANCELLED"
                    safe_trade["estimated_price"] = 0.0
                    
                    await trading_swarm.aupdate_state(config, {
                        "risk_approved": False,
                        "human_approved": False,
                        "proposed_trade": safe_trade
                    })
                
                async for event in trading_swarm.astream(None, config=config, stream_mode="updates"):
                    for node_name, node_state in event.items():
                        messages = node_state.get("messages", [])
                        if messages:
                            content = getattr(messages[-1], "content", str(messages[-1]))
                            await websocket.send_json({"type": "message", "role": "Execution Hub", "content": content})
                
                await websocket.send_json({"type": "message", "role": "System", "content": "Transaction cycle closed."})
                active_thread_id = None 
                continue

            raw_directive = payload.get("directive", "")
            clean_directive = sanitize_raw_input(raw_directive)
            if not clean_directive:
                continue
            
            active_thread_id = f"ws_{id(websocket)}_{uuid.uuid4().hex}"
            config = {"configurable": {"thread_id": active_thread_id}}
            
            initial_state = {
                "messages": [HumanMessage(content=clean_directive)],
                "paper_trading_enabled": payload.get("paper_trading", True),
                "quant_data": {},
                "sentiment_data": {},
                "current_ticker": None,
                "asset_class": "equity", 
                "requested_action": None,
                "requested_quantity": None,
                "requested_allocation": None,
                "risk_threshold": 0.5,
                "proposed_trade": {},
                "risk_approved": False,
                "requires_human_approval": True, # FIX: Added to initialization
                "human_approved": False,         # FIX: Added to initialization
                "errors": []
            }

            PHASE_LABELS = {
                "parser_node": "Parser Agent: Extracting structured parameters from prompt...",
                "sentiment_agent_node": "Sentiment Agent: Scraping news feed & calculating market bias...",
                "quant_agent_node": "Quant Agent: Analyzing technical indicators & volatility...",
                "orchestrator_node": "Orchestrator Agent: Synthesizing swarm intelligence...",
                "risk_agent_node": "Risk Desk: Checking exposure limits & compliance thresholds...",
                "execution_agent_node": "Execution Agent: Order execution ready."
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

                        full_snapshot = await trading_swarm.aget_state(config)
                        snapshot_values = full_snapshot.values or {}

                        extracted_ticker = (
                            node_state.get("current_ticker") or 
                            node_state.get("ticker") or 
                            snapshot_values.get("current_ticker") or
                            (snapshot_values.get("proposed_trade", {}).get("ticker") if isinstance(snapshot_values.get("proposed_trade"), dict) else None)
                        )
                        
                        if extracted_ticker and extracted_ticker != "UNKNOWN":
                            live_data = get_live_asset_data(extracted_ticker)
                            if live_data:
                                await websocket.send_json({
                                    "type": "asset_intelligence",
                                    "data": live_data
                                })

                        raw_sent = node_state.get("sentiment_data") or snapshot_values.get("sentiment_data", {})
                        if isinstance(raw_sent, dict) and raw_sent:
                            payload_sent = raw_sent
                            if extracted_ticker and extracted_ticker in raw_sent:
                                payload_sent = raw_sent[extracted_ticker]
                            elif len(raw_sent) == 1 and isinstance(list(raw_sent.values())[0], dict):
                                payload_sent = list(raw_sent.values())[0]

                            if isinstance(payload_sent, dict) and ("sentiment_label" in payload_sent or "top_headlines" in payload_sent):
                                await websocket.send_json({
                                    "type": "sentiment_data",
                                    "data": payload_sent
                                })

            current_state = await trading_swarm.aget_state(config)
            
            # FIX: Final graph mismatch string replaced.
            if current_state.next and "execution_agent_node" in current_state.next:
                proposed_trade = current_state.values.get("proposed_trade")
                if not isinstance(proposed_trade, dict):
                    proposed_trade = {}
                
                raw_alloc = proposed_trade.get("allocation")
                raw_shrs = proposed_trade.get("shares")
                
                try:
                    alloc_val = float(raw_alloc) if raw_alloc is not None else None
                except (ValueError, TypeError):
                    alloc_val = None
                    
                try:
                    shrs_val = float(raw_shrs) if raw_shrs is not None else None
                except (ValueError, TypeError):
                    shrs_val = None
                
                await websocket.send_json({
                    "type": "checkpoint",
                    "role": "SYSTEM",
                    "content": "⏸️ Pipeline reached Human-in-the-Loop checkpoint. Awaiting authorization.",
                    "trade_details": {
                        "ticker": proposed_trade.get("ticker", "UNKNOWN"),
                        "action": proposed_trade.get("action", "REVIEW"),
                        "allocation": (alloc_val * 100) if alloc_val is not None else "TBD",
                        "shares": shrs_val if shrs_val is not None else "TBD"
                    }
                })
            else:
                await websocket.send_json({
                    "type": "status",
                    "role": "SYSTEM",
                    "content": "✅ Swarm pipeline execution cycle finished."
                })
                active_thread_id = None 

    except (WebSocketDisconnect, RuntimeError):
        print("Socket disconnected.")
    except Exception as e:
        print(f"ERROR inside websocket loop: {e}")
