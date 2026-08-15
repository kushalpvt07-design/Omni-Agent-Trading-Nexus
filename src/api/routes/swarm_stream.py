"""
src.api.routes.swarm_stream — Real-time WebSocket trading pipeline.

Handles the full lifecycle of a swarm trading session:
1. Authenticate via token query parameter
2. Stream directive through all agent nodes
3. Pause at HITL checkpoint for human approval
4. Resume execution or cancel based on user decision
"""

import json
import uuid
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from langchain_core.messages import HumanMessage

from swarm import build_graph
from utils import get_live_asset_data
from src.core.config import logger, audit_logger
from src.core.security import sanitize_raw_input
from src.api.middleware.auth import verify_ws_token
from src.persistence.checkpointer import get_checkpointer

router = APIRouter(tags=["Trading"])


PHASE_LABELS = {
    "parser_node": "Parser Agent: Extracting structured parameters from prompt...",
    "sentiment_agent_node": "Sentiment Agent: Scraping news feed & calculating market bias...",
    "quant_agent_node": "Quant Agent: Analyzing technical indicators & volatility...",
    "orchestrator_node": "Orchestrator Agent: Synthesizing swarm intelligence...",
    "risk_agent_node": "Risk Desk: Checking exposure limits & compliance thresholds...",
    "execution_agent_node": "Execution Agent: Order execution ready.",
}


@router.websocket("/api/v1/swarm-stream")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    # Authenticate before accepting the connection
    if not verify_ws_token(token):
        audit_logger.warning(
            "WebSocket auth failed from %s — closing",
            websocket.client.host if websocket.client else "unknown",
        )
        await websocket.close(code=4003, reason="Authentication failed")
        return

    await websocket.accept()
    audit_logger.info(
        "WebSocket connected from %s",
        websocket.client.host if websocket.client else "unknown",
    )

    trading_swarm = build_graph().compile(
        checkpointer=get_checkpointer(),
        interrupt_before=["execution_agent_node"],
    )

    active_thread_id = None

    try:
        while True:
            data = await websocket.receive_text()

            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "message",
                        "role": "System Alert",
                        "content": "Invalid transmission received. Ignored.",
                    }
                )
                continue

            # ── Human-in-the-Loop Approval/Rejection ────────────
            if payload.get("type") == "human_approval":
                if not active_thread_id:
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "System Alert",
                            "content": "Error: No active trade context.",
                        }
                    )
                    continue

                config = {"configurable": {"thread_id": active_thread_id}}
                current_state = await trading_swarm.aget_state(config)

                if (
                    not current_state.next
                    or "execution_agent_node" not in current_state.next
                ):
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "System Alert",
                            "content": "Error: No active trade pending execution in this thread.",
                        }
                    )
                    continue

                is_approved = payload.get("approved", False)

                if is_approved:
                    audit_logger.info(
                        "HITL APPROVED — thread=%s", active_thread_id
                    )
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "System",
                            "content": "Trade Approved. Dispatching to Execution Agent...",
                        }
                    )
                    await trading_swarm.aupdate_state(
                        config, {"human_approved": True}
                    )
                else:
                    audit_logger.info(
                        "HITL REJECTED — thread=%s", active_thread_id
                    )
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "System Alert",
                            "content": "Trade Rejected by User. Swarm halted.",
                        }
                    )

                    raw_trade = current_state.values.get("proposed_trade", {})
                    safe_trade = (
                        dict(raw_trade) if hasattr(raw_trade, "keys") else {}
                    )

                    safe_trade["action"] = "HOLD"
                    safe_trade["shares"] = None
                    safe_trade["allocation"] = None
                    safe_trade["ticker"] = "CANCELLED"
                    safe_trade["estimated_price"] = 0.0

                    await trading_swarm.aupdate_state(
                        config,
                        {
                            "risk_approved": False,
                            "human_approved": False,
                            "proposed_trade": safe_trade,
                        },
                    )

                async for event in trading_swarm.astream(
                    None, config=config, stream_mode="updates"
                ):
                    for node_name, node_state in event.items():
                        messages = node_state.get("messages", [])
                        if messages:
                            content = getattr(
                                messages[-1], "content", str(messages[-1])
                            )
                            await websocket.send_json(
                                {
                                    "type": "message",
                                    "role": "Execution Hub",
                                    "content": content,
                                }
                            )

                await websocket.send_json(
                    {
                        "type": "message",
                        "role": "System",
                        "content": "Transaction cycle closed.",
                    }
                )
                active_thread_id = None
                continue

            # ── New Directive ───────────────────────────────────
            raw_directive = payload.get("directive", "")
            clean_directive = sanitize_raw_input(raw_directive)
            if not clean_directive:
                continue

            active_thread_id = f"ws_{id(websocket)}_{uuid.uuid4().hex}"
            config = {"configurable": {"thread_id": active_thread_id}}

            audit_logger.info(
                "WS directive deployed — thread=%s directive='%s'",
                active_thread_id,
                clean_directive[:80],
            )

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
                "requires_human_approval": True,
                "human_approved": False,
                "errors": [],
            }

            # ── Stream through agent pipeline ───────────────────
            async for event in trading_swarm.astream(
                initial_state, config=config, stream_mode="updates"
            ):
                for node_name, node_state in event.items():
                    phase_text = PHASE_LABELS.get(
                        node_name, f"Executing node: {node_name}..."
                    )
                    await websocket.send_json(
                        {
                            "type": "status",
                            "role": "SYSTEM",
                            "content": f"⚡ [PHASE ENTERED] {phase_text}",
                        }
                    )

                    if isinstance(node_state, dict):
                        errors = node_state.get("errors", [])
                        if errors:
                            for err in errors:
                                await websocket.send_json(
                                    {
                                        "type": "message",
                                        "role": "SYSTEM ERROR",
                                        "content": f"🚨 {err}",
                                    }
                                )

                        # Fetch and send asset/sentiment data
                        full_snapshot = await trading_swarm.aget_state(config)
                        snapshot_values = full_snapshot.values or {}

                        extracted_ticker = (
                            node_state.get("current_ticker")
                            or node_state.get("ticker")
                            or snapshot_values.get("current_ticker")
                            or (
                                snapshot_values.get("proposed_trade", {}).get(
                                    "ticker"
                                )
                                if isinstance(
                                    snapshot_values.get("proposed_trade"), dict
                                )
                                else None
                            )
                        )

                        if extracted_ticker and extracted_ticker != "UNKNOWN":
                            live_data = await asyncio.to_thread(
                                get_live_asset_data, extracted_ticker
                            )
                            if live_data:
                                await websocket.send_json(
                                    {
                                        "type": "asset_intelligence",
                                        "data": live_data,
                                    }
                                )

                        # Construct unified consensus payload
                        raw_sent = node_state.get(
                            "sentiment_data"
                        ) or snapshot_values.get("sentiment_data", {})
                        payload_sent = {}

                        if isinstance(raw_sent, dict) and raw_sent:
                            if (
                                extracted_ticker
                                and extracted_ticker in raw_sent
                            ):
                                payload_sent = dict(raw_sent[extracted_ticker])
                            elif len(raw_sent) == 1 and isinstance(
                                list(raw_sent.values())[0], dict
                            ):
                                payload_sent = dict(
                                    list(raw_sent.values())[0]
                                )
                            else:
                                payload_sent = dict(raw_sent)

                        # Extract reasoning from orchestrator's proposed_trade
                        current_proposed = (
                            node_state.get("proposed_trade")
                            or snapshot_values.get("proposed_trade")
                            or {}
                        )
                        if isinstance(current_proposed, dict) and current_proposed.get(
                            "reasoning"
                        ):
                            payload_sent["reasoning"] = current_proposed.get(
                                "reasoning"
                            )

                        # Dispatch sentiment/reasoning if available
                        if payload_sent and (
                            "sentiment_label" in payload_sent
                            or "top_headlines" in payload_sent
                            or "reasoning" in payload_sent
                        ):
                            await websocket.send_json(
                                {
                                    "type": "sentiment_data",
                                    "data": payload_sent,
                                }
                            )

                        # Send terminal message
                        messages = node_state.get("messages", [])
                        if messages:
                            content = getattr(
                                messages[-1], "content", str(messages[-1])
                            )
                            agent_role = (
                                node_name.replace("_node", "")
                                .replace("_agent", "")
                                .upper()
                            )

                            await websocket.send_json(
                                {
                                    "type": "message",
                                    "role": agent_role,
                                    "content": content,
                                }
                            )

            # ── Post-pipeline: checkpoint or complete ───────────
            current_state = await trading_swarm.aget_state(config)

            if (
                current_state.next
                and "execution_agent_node" in current_state.next
            ):
                proposed_trade = current_state.values.get("proposed_trade")
                if not isinstance(proposed_trade, dict):
                    proposed_trade = {}

                raw_alloc = proposed_trade.get("allocation")
                raw_shrs = proposed_trade.get("shares")

                try:
                    alloc_val = (
                        float(raw_alloc) if raw_alloc is not None else None
                    )
                except (ValueError, TypeError):
                    alloc_val = None

                try:
                    shrs_val = (
                        float(raw_shrs) if raw_shrs is not None else None
                    )
                except (ValueError, TypeError):
                    shrs_val = None

                await websocket.send_json(
                    {
                        "type": "checkpoint",
                        "role": "SYSTEM",
                        "content": "⏸️ Pipeline reached Human-in-the-Loop checkpoint. Awaiting authorization.",
                        "trade_details": {
                            "ticker": proposed_trade.get("ticker", "UNKNOWN"),
                            "action": proposed_trade.get("action", "REVIEW"),
                            "allocation": (alloc_val * 100)
                            if alloc_val is not None
                            else "TBD",
                            "shares": shrs_val
                            if shrs_val is not None
                            else "TBD",
                        },
                    }
                )
            else:
                await websocket.send_json(
                    {
                        "type": "pipeline_complete",
                        "role": "SYSTEM",
                        "content": "✅ Swarm pipeline execution cycle finished.",
                    }
                )
                active_thread_id = None

    except (WebSocketDisconnect, RuntimeError):
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("Unhandled error in WebSocket loop")
