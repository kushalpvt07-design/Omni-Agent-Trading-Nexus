import json
import math
import asyncio
import logging
from langchain_core.messages import AIMessage
from src.state import FinancialSwarmState
from src.core.market_data import get_latest_prices, to_usd_price
from src.core.telemetry import Timer, telemetry

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
    with Timer("risk_agent_node") as timer:
        if state.get("errors"):
            return {
                "risk_approved": False,
                "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
            }

        trade = state.get("proposed_trade", {})
        action = trade.get("action", "HOLD")

        raw_shares = trade.get("shares")
        shares = float(raw_shares) if raw_shares is not None else 0.0

        raw_alloc = trade.get("allocation")
        try:
            allocation = float(raw_alloc) if raw_alloc is not None else 0.0
            if allocation > 1.0:
                allocation = allocation / 100.0
            allocation = max(0.0, min(1.0, allocation))
        except (ValueError, TypeError):
            allocation = 0.0

        if shares < 0:
            shares = 0.0

        ticker = state.get("current_ticker", "UNKNOWN")
        asset_class = state.get("asset_class", "equity")

        if action in ["HOLD", "REJECT"]:
            return {
                "risk_approved": False,
                "messages": [
                    AIMessage(
                        content=f"🛡️ Risk Desk: Acknowledged orchestration directive to {action}."
                    )
                ],
                "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
            }

        quant_data = state.get("quant_data", {}).get(ticker, "")
        live_price_native = 0.0
        annualized_vol = 0.0
        daily_vol_from_quant = 0.0

        if quant_data:
            try:
                parsed_quant = (
                    json.loads(quant_data) if isinstance(quant_data, str) else quant_data
                )
                live_price_native = float(parsed_quant.get("latest_close", 0.0))
                vol_metrics = parsed_quant.get("volatility_metrics", {})
                annualized_vol = float(vol_metrics.get("annualized_volatility", 0.0))
                daily_vol_from_quant = float(vol_metrics.get("daily_log_return_std", 0.0))
            except Exception as e:
                logger.warning("Risk Desk failed to parse quant_data for %s: %s", ticker, e)

        if live_price_native <= 0.0:
            telemetry.record_error("RISK_MISSING_LIVE_PRICE")
            return {
                "risk_approved": False,
                "errors": [
                    f"FATAL: Risk Desk could not resolve live price for {ticker}. Aborting."
                ],
                "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
            }

        # Convert native price (e.g., INR for .NS/.BO) to USD for ledger math (BUG-003)
        live_price_usd = await asyncio.to_thread(to_usd_price, live_price_native, ticker)

        ledger = get_ledger_data(user_id=state.get("user_id"))
        cash_available = float(ledger["cash"])
        positions = ledger["positions"]

        if action == "SELL":
            owned_shares = float(positions.get(ticker, 0.0))
            if owned_shares <= 0.0:
                telemetry.record_error("RISK_NAKED_SHORT_REJECTED")
                reject_msg = (
                    f"⛔ RISK DESK REJECTION: Attempted to SELL {ticker}, but ledger shows "
                    f"0 shares owned. Naked shorting is prohibited. Overriding to HOLD."
                )
                overridden_trade = {
                    **trade,
                    "action": "HOLD",
                    "allocation": 0.0,
                    "shares": 0.0,
                    "estimated_price": live_price_native,
                    "reasoning": f"[RISK REJECTION: Naked shorting prohibited] {trade.get('reasoning', '')}",
                }
                return {
                    "risk_approved": False,
                    "proposed_trade": overridden_trade,
                    "messages": [AIMessage(content=reject_msg)],
                    "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
                }

            if shares <= 0.0 and allocation > 0:
                sell_shares = round(owned_shares * allocation, 4)
            elif shares > 0:
                sell_shares = round(shares, 4)
            else:
                sell_shares = round(owned_shares, 4)

            if sell_shares > owned_shares + 1e-6:
                telemetry.record_error("RISK_OVERSELL_REJECTED")
                reject_msg = (
                    f"⛔ RISK DESK REJECTION: Attempted to SELL {sell_shares} of {ticker}, "
                    f"but ledger only shows {owned_shares} shares owned. Overriding to HOLD."
                )
                overridden_trade = {
                    **trade,
                    "action": "HOLD",
                    "allocation": 0.0,
                    "shares": 0.0,
                    "estimated_price": live_price_native,
                    "reasoning": f"[RISK REJECTION: Insufficient shares for sell order] {trade.get('reasoning', '')}",
                }
                return {
                    "risk_approved": False,
                    "proposed_trade": overridden_trade,
                    "messages": [AIMessage(content=reject_msg)],
                    "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
                }

            approve_msg = (
                f"✅ RISK DESK APPROVAL: Valid SELL order for {sell_shares} shares of {ticker}. "
                f"Inventory verified. Routing to Human Checkpoint."
            )
            updated_trade = trade.copy()
            updated_trade["estimated_price"] = live_price_native
            updated_trade["shares"] = min(sell_shares, owned_shares)

            return {
                "risk_approved": True,
                "proposed_trade": updated_trade,
                "messages": [AIMessage(content=approve_msg)],
                "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
            }

        # ── BUY LOGIC ───────────────────────────────────────────────

        # 1. Enforce user-specified volatility risk_threshold (BUG-005)
        raw_user_threshold = state.get("risk_threshold")
        if raw_user_threshold is not None:
            user_threshold = float(raw_user_threshold)
            if user_threshold > 1.0:
                user_threshold = user_threshold / 100.0
            if annualized_vol > user_threshold:
                telemetry.record_error("RISK_VOL_THRESHOLD_EXCEEDED")
                reject_msg = (
                    f"⛔ RISK DESK REJECTION: {ticker} annualized volatility ({annualized_vol * 100:.1f}%) "
                    f"exceeds your specified risk threshold ({user_threshold * 100:.1f}%). Overriding to HOLD."
                )
                overridden_trade = {
                    **trade,
                    "action": "HOLD",
                    "allocation": 0.0,
                    "shares": 0.0,
                    "estimated_price": live_price_native,
                    "reasoning": (
                        f"[RISK REJECTION: Volatility {annualized_vol * 100:.1f}% > "
                        f"Threshold {user_threshold * 100:.1f}%] {trade.get('reasoning', '')}"
                    ),
                }
                return {
                    "risk_approved": False,
                    "proposed_trade": overridden_trade,
                    "messages": [AIMessage(content=reject_msg)],
                    "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
                }

        # 2. Properly price all held positions in USD to compute true total_equity (BUG-001)
        other_tickers = [t for t, s in positions.items() if float(s) > 0 and t != ticker]
        other_prices_usd = {}
        if other_tickers:
            other_prices_usd = await asyncio.to_thread(
                get_latest_prices, other_tickers, True
            )

        target_position_value_usd = float(positions.get(ticker, 0.0)) * live_price_usd
        other_positions_value_usd = 0.0
        for other_t, other_s in positions.items():
            if other_t == ticker or float(other_s) <= 0:
                continue
            px_usd = other_prices_usd.get(other_t, 0.0)
            if px_usd <= 0.0 and state.get("user_id") is not None:
                from src.persistence.database import get_db
                with get_db() as conn:
                    row = conn.execute(
                        "SELECT avg_cost FROM user_positions WHERE user_id = ? AND ticker = ?",
                        (state.get("user_id"), other_t),
                    ).fetchone()
                    if row and row["avg_cost"]:
                        px_usd = float(row["avg_cost"])
            other_positions_value_usd += float(other_s) * px_usd

        total_equity = cash_available + target_position_value_usd + other_positions_value_usd
        if total_equity <= 0:
            total_equity = cash_available

        # 3. Volatility-targeted position limit (BUG-008)
        TARGET_DAILY_VOL = 0.01   # 1% daily portfolio volatility budget
        MAX_ALLOCATION = 0.30     # hard cap: never more than 30% of equity in one name
        MIN_ALLOCATION = 0.02     # minimum position floor: 2%

        annualization_days = 365.0 if asset_class == "crypto" or "/" in ticker else 252.0
        if daily_vol_from_quant > 0:
            asset_daily_vol = daily_vol_from_quant
        elif annualized_vol > 0:
            asset_daily_vol = annualized_vol / math.sqrt(annualization_days)
        else:
            asset_daily_vol = 0.0

        if asset_daily_vol > 0:
            allocation_pct = min(MAX_ALLOCATION, TARGET_DAILY_VOL / asset_daily_vol)
        else:
            allocation_pct = 0.10
        allocation_pct = max(MIN_ALLOCATION, allocation_pct)

        existing_weight = target_position_value_usd / total_equity if total_equity > 0 else 0.0
        remaining_vol_capacity = max(0.0, allocation_pct - existing_weight)

        # 4. Determine trade value in USD (auto-size if user did not specify quantity/allocation)
        user_specified_qty = state.get("requested_quantity") is not None and float(state.get("requested_quantity") or 0) > 0
        user_specified_alloc = state.get("requested_allocation") is not None and float(state.get("requested_allocation") or 0) > 0

        if shares > 0:
            requested_trade_value_usd = shares * live_price_usd
            actual_allocation = requested_trade_value_usd / total_equity if total_equity > 0 else 1.0
        elif user_specified_alloc:
            actual_allocation = allocation
            requested_trade_value_usd = total_equity * actual_allocation
        else:
            # Default unspecified allocation: auto-size to min(10%, remaining vol capacity, available cash fraction)
            cash_fraction = cash_available / total_equity if total_equity > 0 else 0.0
            actual_allocation = min(0.10, remaining_vol_capacity, cash_fraction)
            requested_trade_value_usd = total_equity * actual_allocation

        # Overdraft guard against available USD cash
        if action == "BUY" and (requested_trade_value_usd > cash_available + 1e-6 or requested_trade_value_usd <= 0):
            telemetry.record_error("RISK_INSUFFICIENT_CASH")
            reject_msg = (
                f"⛔ RISK DESK REJECTION: Requested trade value (${requested_trade_value_usd:,.2f} USD) "
                f"exceeds available cash (${cash_available:,.2f} USD) or remaining capacity. Overriding to HOLD."
            )
            overridden_trade = {
                **trade,
                "action": "HOLD",
                "allocation": 0.0,
                "shares": 0.0,
                "estimated_price": live_price_native,
                "reasoning": "[RISK REJECTION: Insufficient Cash]",
            }
            return {
                "risk_approved": False,
                "proposed_trade": overridden_trade,
                "messages": [AIMessage(content=reject_msg)],
                "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
            }

        combined_exposure_fraction = (
            (requested_trade_value_usd + target_position_value_usd) / total_equity
            if total_equity > 0
            else 1.0
        )
        max_allowed_spend_usd = total_equity * allocation_pct

        logger.info(
            "Risk analysis for %s %s: alloc=%.1f%% requested=$%,.2f max_allowed=$%,.2f vol=%.1f%%",
            action,
            ticker,
            actual_allocation * 100,
            requested_trade_value_usd,
            max_allowed_spend_usd,
            annualized_vol * 100,
        )

        if action == "BUY" and combined_exposure_fraction > allocation_pct + 1e-6:
            telemetry.record_error("RISK_CONCENTRATION_LIMIT")
            reject_msg = (
                f"⛔ RISK DESK REJECTION: Combined exposure "
                f"(${requested_trade_value_usd + target_position_value_usd:,.2f} / {combined_exposure_fraction * 100:.1f}% of equity) "
                f"exceeds the vol-targeted limit (${max_allowed_spend_usd:,.2f} / {allocation_pct * 100:.1f}%). Overriding to HOLD."
            )
            original_reasoning = trade.get("reasoning", "No original reasoning provided.")

            overridden_trade = {
                "ticker": ticker,
                "action": "HOLD",
                "allocation": 0.0,
                "shares": 0.0,
                "estimated_price": live_price_native,
                "reasoning": f"[RISK REJECTION: Exceeds vol-targeted equity limit] Original LLM Analysis: {original_reasoning}",
            }
            return {
                "risk_approved": False,
                "proposed_trade": overridden_trade,
                "messages": [AIMessage(content=reject_msg)],
                "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
            }

        approve_msg = (
            f"✅ RISK DESK APPROVAL: Trade size (${requested_trade_value_usd:,.2f} USD) "
            f"is within compliance limits (Cap: {allocation_pct * 100:.1f}%). Routing to Human Checkpoint."
        )

        updated_trade = trade.copy()
        updated_trade["estimated_price"] = live_price_native
        updated_trade["allocation"] = round(actual_allocation, 4)

        if not updated_trade.get("shares"):
            updated_trade["shares"] = round(requested_trade_value_usd / live_price_usd, 4)
        else:
            updated_trade["shares"] = round(float(updated_trade["shares"]), 4)

        return {
            "risk_approved": True,
            "proposed_trade": updated_trade,
            "messages": [AIMessage(content=approve_msg)],
            "node_latencies_ms": {"risk_agent_node": timer.elapsed_ms},
        }
