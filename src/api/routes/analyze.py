"""
src.api.routes.analyze — Stateless single-shot trade analysis endpoint.

Accepts a natural-language trading directive, runs it through the
full swarm pipeline (without HITL checkpoint), and returns the result.
"""

from fastapi import APIRouter, HTTPException, Depends

from schemas import TradeRequest, TradeResponse
from langchain_core.messages import HumanMessage
from swarm import build_graph
from src.core.config import logger, audit_logger
from src.core.security import sanitize_raw_input
from src.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/api/v1", tags=["Trading"])

# Lazy-initialized stateless swarm (no checkpointer, no HITL)
_stateless_swarm = None


def _get_stateless_swarm():
    global _stateless_swarm
    if _stateless_swarm is None:
        _stateless_swarm = build_graph().compile()
    return _stateless_swarm


@router.post("/analyze", response_model=TradeResponse)
async def analyze_trade(request: TradeRequest, _=Depends(verify_api_key)):
    audit_logger.info("REST /api/v1/analyze — directive received")
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
            "requires_human_approval": True,
            "human_approved": False,
            "errors": [],
        }

        final_state = await _get_stateless_swarm().ainvoke(initial_state)

        if final_state.get("errors"):
            return TradeResponse(
                status="ERROR",
                error_message=" | ".join(final_state["errors"]),
            )

        proposed_trade = final_state.get("proposed_trade")
        if not isinstance(proposed_trade, dict):
            proposed_trade = {}

        ticker = (
            proposed_trade.get("ticker")
            or final_state.get("current_ticker")
            or "UNKNOWN"
        )

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
            orchestrator_reasoning=proposed_trade.get(
                "reasoning", "No reasoning provided."
            ),
        )
    except Exception as e:
        logger.exception("Swarm execution failed on /api/v1/analyze")
        raise HTTPException(
            status_code=500, detail=f"Swarm execution failed: {str(e)}"
        )
