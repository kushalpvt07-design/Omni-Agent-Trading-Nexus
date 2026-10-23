import json
import logging
from pydantic import BaseModel, Field
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)
from src.state import FinancialSwarmState
from src.core.telemetry import Timer, telemetry

logger = logging.getLogger("omni-nexus.orchestrator")


class OrchestratorDirective(BaseModel):
    action: Literal["BUY", "SELL", "HOLD", "REJECT"] = Field(...)
    reasoning: str


def _is_retryable_llm_error(exc: BaseException) -> bool:
    """Only retry transient rate-limit (429) or server (5xx) errors, never 404/auth errors."""
    msg = str(exc).lower()
    if any(code in msg for code in ("404", "not_found", "not found", "401", "403", "invalid argument")):
        return False
    return True


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_retryable_llm_error),
    reraise=True,
)
async def _invoke_llm_with_backoff(structured_llm, system_prompt: str, analysis_context: str):
    return await structured_llm.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_context),
        ]
    )


async def orchestrator_node(state: FinancialSwarmState) -> dict:
    with Timer("orchestrator_node") as timer:
        if state.get("errors"):
            upstream_errors = state.get("errors", [])
            error_summary = "\n".join(f"• {e}" for e in upstream_errors)
            return {
                "proposed_trade": {
                    "ticker": state.get("current_ticker", "UNKNOWN"),
                    "action": "REJECT",
                    "allocation": None,
                    "shares": None,
                    "estimated_price": 0.0,
                    "reasoning": f"Rejected due to upstream errors: {error_summary}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            f"🚨 **Orchestrator: Analysis Halted**\n\n"
                            f"The swarm encountered errors before reaching the orchestrator:\n"
                            f"{error_summary}\n\n"
                            f"**Action:** REJECT — No trade will be executed."
                        )
                    )
                ],
                "node_latencies_ms": {"orchestrator_node": timer.elapsed_ms},
            }

        user_request = "No request."
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                user_request = msg.content
                break

        active_ticker = state.get("current_ticker", "UNKNOWN")
        raw_quant = state.get("quant_data", {}).get(active_ticker, "No data available.")
        raw_sentiment = state.get("sentiment_data", {}).get(
            active_ticker, "No data available."
        )

        # Deterministic pre-check on quant data integrity before invoking LLM
        try:
            parsed_q = json.loads(raw_quant) if isinstance(raw_quant, str) else raw_quant
            if (
                not isinstance(parsed_q, dict)
                or parsed_q.get("status") != "success"
                or float(parsed_q.get("latest_close", 0.0)) <= 0
                or float(parsed_q.get("latest_volume", 0.0)) <= 0
            ):
                return {
                    "proposed_trade": {
                        "ticker": active_ticker,
                        "action": "REJECT",
                        "allocation": None,
                        "shares": None,
                        "estimated_price": 0.0,
                        "reasoning": "Quantitative telemetry is missing, corrupted, or reported 0 volume.",
                    },
                    "messages": [
                        AIMessage(
                            content=(
                                f"🚨 **Orchestrator: Data Integrity Rejection for {active_ticker}**\n\n"
                                f"Quantitative data is missing or shows zero trading volume. Outputting **REJECT**."
                            )
                        )
                    ],
                    "node_latencies_ms": {"orchestrator_node": timer.elapsed_ms},
                }
        except Exception:
            pass

        requested_quantity = state.get("requested_quantity")
        raw_alloc = state.get("requested_allocation")

        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
        ]

        system_prompt = (
            "You are an elite autonomous financial orchestrator.\n"
            "Analyze the provided quantitative data and qualitative market sentiment to make a final trading decision.\n"
            "CRITICAL RULES:\n"
            "1. If the quantitative data is missing, corrupted, or shows 0 volume, you MUST output action='REJECT'.\n"
            "2. CONFLICT RESOLUTION PROTOCOL: Quantitative price, volatility, RSI, and SMA telemetry carry 65% weight; "
            "Qualitative news sentiment carries 35% weight. If sentiment is degraded/unavailable, rely 100% on quantitative metrics. "
            "If quantitative indicators (e.g., severe downtrend below 30-day SMA + overbought RSI > 75) strongly contradict a bullish "
            "sentiment or a user's BUY request, output 'HOLD' and explain the conflict clearly.\n"
            "3. NEVER invent prices, volumes, or indicators not present in the provided data.\n"
            "4. Your decision can confirm the user's direction or downgrade it to 'HOLD' or 'REJECT', but must never flip BUY to SELL or SELL to BUY."
        )

        analysis_context = (
            f"User Request: {user_request}\n\n"
            f"Target Ticker: {active_ticker}\n\n"
            f"Quantitative Data (Chronological Oldest->Newest): {raw_quant}\n\n"
            f"Qualitative Sentiment Data: {raw_sentiment}"
        )

        logger.info("Orchestrator analyzing swarm data for %s", active_ticker)

        decision = None
        last_error = None
        for model_name in models_to_try:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=0.0,
                    max_retries=0,
                )
                structured_llm = llm.with_structured_output(OrchestratorDirective)
                decision = await _invoke_llm_with_backoff(
                    structured_llm, system_prompt, analysis_context
                )
                if decision:
                    break
            except Exception as e:
                logger.warning("Model %s failed in orchestrator_node: %s", model_name, e)
                last_error = e
                continue

        try:
            if not decision:
                raise last_error or RuntimeError("All configured Gemini models failed")

            if decision.action == "REJECT":
                final_action = "REJECT"
                final_shares = None
                final_allocation = None
            else:
                requested_action = state.get("requested_action") or decision.action
                if requested_action in ("BUY", "SELL") and decision.action not in (
                    requested_action,
                    "HOLD",
                    "REJECT",
                ):
                    logger.warning(
                        "Orchestrator tried to flip action %s → %s for %s; overriding to HOLD.",
                        requested_action,
                        decision.action,
                        active_ticker,
                    )
                    decision_action = "HOLD"
                else:
                    decision_action = decision.action

                final_action = decision_action

                if requested_quantity is not None and float(requested_quantity) > 0:
                    final_shares = float(requested_quantity)
                    final_allocation = None
                else:
                    final_shares = None
                    if final_action == "SELL":
                        final_allocation = float(raw_alloc) if raw_alloc is not None else None
                    else:
                        try:
                            final_allocation = (
                                float(raw_alloc) if raw_alloc is not None else 0.1
                            )
                        except (ValueError, TypeError):
                            final_allocation = 0.1

            proposed_trade = {
                "ticker": active_ticker,
                "action": final_action,
                "allocation": final_allocation,
                "shares": final_shares,
                "estimated_price": 0.0,
                "reasoning": decision.reasoning,
            }

            report_qty = (
                f"{final_shares} Shares"
                if final_shares
                else f"{final_allocation * 100:.1f}% Allocation"
                if final_allocation
                else "N/A"
            )

            final_report = (
                f"**AI Swarm Analysis Complete for {active_ticker}**\n\n"
                f"**Action:** {final_action} {report_qty}\n"
                f"**Reasoning:** {decision.reasoning}"
            )

            return {
                "proposed_trade": proposed_trade,
                "messages": [AIMessage(content=final_report)],
                "node_latencies_ms": {"orchestrator_node": timer.elapsed_ms},
            }

        except Exception as e:
            telemetry.record_error("ORCHESTRATOR_LLM_ERROR")
            err_msg = f"STATUS: ERROR - LLM Timeout/Rate Limit Exceeded: {str(e)}"
            logger.exception("Orchestrator LLM invocation failed for %s", active_ticker)
            return {
                "errors": [err_msg],
                "messages": [AIMessage(content=f"🚨 Orchestrator Error: {err_msg}")],
                "node_latencies_ms": {"orchestrator_node": timer.elapsed_ms},
            }
