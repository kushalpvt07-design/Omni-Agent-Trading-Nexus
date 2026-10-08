import json
import math
import logging
from langchain_core.messages import AIMessage
from src.state import FinancialSwarmState

logger = logging.getLogger("omni-nexus.risk")


def get_ledger_data(user_id: int | None = None) -> dict:
    """Read the portfolio ledger for the given user from SQLite.

    Returns safe defaults if user_id is not provided or data is unavailable.
    """
    if user_id is not None:
        from src.persistence.user_portfolio import get_user_ledger
        return get_user_ledger(user_id)
    return {"cash": 100000.0, "positions": {}}


async def risk_agent_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {"risk_approved": False}

    trade = state.get("proposed_trade", {})
    action = trade.get("action", "HOLD")

    raw_shares = trade.get("shares")
    shares = float(raw_shares) if raw_shares is not None else 0.0

    raw_alloc = trade.get("allocation")
    # §1.6 — Clamp allocation to [0, 1]; LLMs sometimes return 50 for "50%"
    try:
        allocation = float(raw_alloc) if raw_alloc is not None else 0.0
        allocation = max(0.0, min(1.0, allocation))
    except (ValueError, TypeError):
        allocation = 0.0

    # §1.6 — Reject impossible negative share quantities
    if shares < 0:
        shares = 0.0

    ticker = state.get("current_ticker", "UNKNOWN")

    # §1.7 — HOLD / REJECT: no trade, mark risk NOT approved (semantically correct)
    if action in ["HOLD", "REJECT"]:
        return {
            "risk_approved": False,
            "messages": [AIMessage(content=f"🛡️ Risk Desk: Acknowledged orchestration directive to {action}.")],
        }

    quant_data = state.get("quant_data", {}).get(ticker, "")
    live_price = 0.0
    annualized_vol = 0.0

    if quant_data:
        try:
            parsed_quant = json.loads(quant_data)
            live_price = float(parsed_quant.get("latest_close", 0.0))
            # §1.1 / §1.2 — use annualized log-return volatility (full precision)
            annualized_vol = float(
                parsed_quant.get("volatility_metrics", {}).get(
                    "annualized_volatility", 0.0
                )
            )
        except Exception:
            pass

    if live_price <= 0.0:
        return {
            "risk_approved": False,
            "errors": [f"FATAL: Risk Desk could not resolve live price for {ticker}. Aborting."],
        }

    ledger = get_ledger_data(user_id=state.get("user_id"))
    cash_available = ledger["cash"]
    positions = ledger["positions"]

    if action == "SELL":
        owned_shares = float(positions.get(ticker, 0.0))
        if owned_shares <= 0.0:
            reject_msg = f"⛔ RISK DESK REJECTION: Attempted to SELL {ticker}, but ledger shows 0 shares owned. Naked shorting is prohibited. Overriding to HOLD."
            overridden_trade = {
                **trade,
                "action": "HOLD",
                "allocation": 0.0,
                "shares": 0.0,
                "estimated_price": live_price,
                "reasoning": f"[RISK REJECTION: Naked shorting prohibited] {trade.get('reasoning', '')}",
            }
            return {
                "risk_approved": False,
                "proposed_trade": overridden_trade,
                "messages": [AIMessage(content=reject_msg)],
            }

        # §1.5 — SELL default: 100% of position when no specific quantity given.
        # allocation=0.1 on the orchestrator path means "use allocation fraction",
        # but if neither shares nor allocation was provided by the user, sell all.
        if shares <= 0.0 and allocation > 0:
            sell_shares = owned_shares * allocation
        elif shares > 0:
            sell_shares = shares
        else:
            # No quantity at all — sell the entire position
            sell_shares = owned_shares

        if sell_shares > owned_shares:
            reject_msg = f"⛔ RISK DESK REJECTION: Attempted to SELL {sell_shares} of {ticker}, but ledger only shows {owned_shares} shares owned. Overriding to HOLD."
            overridden_trade = {
                **trade,
                "action": "HOLD",
                "allocation": 0.0,
                "shares": 0.0,
                "estimated_price": live_price,
                "reasoning": f"[RISK REJECTION: Insufficient shares for sell order] {trade.get('reasoning', '')}",
            }
            return {
                "risk_approved": False,
                "proposed_trade": overridden_trade,
                "messages": [AIMessage(content=reject_msg)],
            }

        approve_msg = f"✅ RISK DESK APPROVAL: Valid SELL order for {ticker}. Inventory verified. Routing to Human Checkpoint."
        updated_trade = trade.copy()
        updated_trade["estimated_price"] = live_price
        updated_trade["shares"] = sell_shares

        return {
            "risk_approved": True,
            "proposed_trade": updated_trade,
            "messages": [AIMessage(content=approve_msg)],
        }

    # ── BUY LOGIC ───────────────────────────────────────────────
    # §1.4 — Size limits are now a percentage of *total equity* (cash + market
    # value of all positions), not just remaining cash. This prevents the
    # compounding-buy exploit where one ticker can grow to 100% of the portfolio.
    existing_market_value = sum(
        float(v) * live_price if k == ticker else 0.0
        for k, v in positions.items()
    )
    # Fetch current market value of the target position from the ledger
    target_position_value = float(positions.get(ticker, 0.0)) * live_price
    total_equity = cash_available + sum(
        # Approximate other positions at their share count (no live prices here)
        # For the concentration check, the key exposure is the target ticker.
        float(v) * live_price if k == ticker else float(v)
        for k, v in positions.items()
    )
    if total_equity <= 0:
        total_equity = cash_available

    if shares > 0:
        requested_trade_value = shares * live_price
        actual_allocation = requested_trade_value / total_equity if total_equity > 0 else 1.0
    else:
        actual_allocation = allocation if allocation > 0 else 0.1
        requested_trade_value = cash_available * actual_allocation

    # Overdraft guard — still checks against available cash
    if action == "BUY" and requested_trade_value > cash_available:
        reject_msg = f"⛔ RISK DESK REJECTION: Requested trade value (${requested_trade_value:,.2f}) exceeds total available cash (${cash_available:,.2f}). Overriding to HOLD."
        overridden_trade = {
            **trade,
            "action": "HOLD",
            "allocation": 0.0,
            "shares": 0.0,
            "estimated_price": live_price,
            "reasoning": "[RISK REJECTION: Insufficient Cash]",
        }
        return {
            "risk_approved": False,
            "proposed_trade": overridden_trade,
            "messages": [AIMessage(content=reject_msg)],
        }

    # §1.3 — Vol-targeting: allocation_pct = target_vol / asset_vol, capped.
    # Target daily vol = 1% of portfolio. Minimum position size = 2%.
    TARGET_DAILY_VOL = 0.01   # 1% daily portfolio volatility budget
    MAX_ALLOCATION = 0.30     # hard cap: never more than 30% of equity in one name
    MIN_ALLOCATION = 0.02     # floors position at 2% — low enough to reflect real risk

    if annualized_vol > 0:
        asset_daily_vol = annualized_vol / math.sqrt(252)
        allocation_pct = min(MAX_ALLOCATION, TARGET_DAILY_VOL / asset_daily_vol)
    else:
        # Unknown vol: fall back to a conservative 10%
        allocation_pct = 0.10
    allocation_pct = max(MIN_ALLOCATION, allocation_pct)

    # §1.4 — Concentration check: include the position already held in the name
    combined_exposure_fraction = (
        (requested_trade_value + target_position_value) / total_equity
        if total_equity > 0 else 1.0
    )
    max_allowed_spend = total_equity * allocation_pct

    logger.info(
        "Risk analysis for %s %s: alloc=%.1f%% requested=$%,.2f max_allowed=$%,.2f vol=%.1f%%",
        action, ticker, actual_allocation * 100, requested_trade_value, max_allowed_spend,
        annualized_vol * 100,
    )

    if action == "BUY" and combined_exposure_fraction > allocation_pct:
        reject_msg = (
            f"⛔ RISK DESK REJECTION: Combined exposure (${requested_trade_value + target_position_value:,.2f} / {combined_exposure_fraction*100:.1f}% of equity) "
            f"exceeds the vol-targeted limit (${max_allowed_spend:,.2f} / {allocation_pct*100:.1f}%). Overriding to HOLD."
        )
        original_reasoning = trade.get("reasoning", "No original reasoning provided.")

        overridden_trade = {
            "ticker": ticker,
            "action": "HOLD",
            "allocation": 0.0,
            "shares": 0.0,
            "estimated_price": live_price,
            "reasoning": f"[RISK REJECTION: Exceeds vol-targeted equity limit] Original LLM Analysis: {original_reasoning}",
        }
        return {
            "risk_approved": False,
            "proposed_trade": overridden_trade,
            "messages": [AIMessage(content=reject_msg)],
        }

    approve_msg = f"✅ RISK DESK APPROVAL: Trade size (${requested_trade_value:,.2f}) is within compliance limits. Routing to Human Checkpoint."

    updated_trade = trade.copy()
    updated_trade["estimated_price"] = live_price
    updated_trade["allocation"] = actual_allocation

    # Set exact shares for execution agent
    if not updated_trade.get("shares"):
        updated_trade["shares"] = requested_trade_value / live_price

    return {
        "risk_approved": True,
        "proposed_trade": updated_trade,
        "messages": [AIMessage(content=approve_msg)],
    }
