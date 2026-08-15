import os
import asyncio
import logging
from pydantic import BaseModel, Field
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.state import FinancialSwarmState
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("omni-nexus.orchestrator")


class OrchestratorDirective(BaseModel):
    action: Literal["BUY", "SELL", "HOLD", "REJECT"] = Field(...)
    reasoning: str


@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=2, min=4, max=30),
)
async def _invoke_llm_with_backoff(structured_llm, system_prompt, analysis_context):
    return await structured_llm.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_context),
        ]
    )


async def orchestrator_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {
            "messages": [
                AIMessage(content="🚨 Orchestrator skipped due to upstream errors.")
            ]
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

    requested_quantity = state.get("requested_quantity")
    raw_alloc = state.get("requested_allocation")

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]

    primary_llm = ChatGoogleGenerativeAI(model=models_to_try[0])
    structured_llm = primary_llm.with_structured_output(OrchestratorDirective)

    fallbacks = [
        ChatGoogleGenerativeAI(model=m).with_structured_output(OrchestratorDirective)
        for m in models_to_try[1:]
    ]
    structured_llm = structured_llm.with_fallbacks(fallbacks)

    system_prompt = (
        "You are an elite autonomous financial orchestrator. "
        "Analyze the provided quantitative data and qualitative market sentiment to make a final trading decision. "
        "CRITICAL RULE: If the quantitative data is missing, corrupted, or shows 0 volume, you MUST output action='REJECT'. "
        "Your decision overrides the user's initial request. If the data looks bad, you must REJECT or HOLD."
    )

    analysis_context = (
        f"User Request: {user_request}\n\n"
        f"Target Ticker: {active_ticker}\n\n"
        f"Quantitative Data: {raw_quant}\n\n"
        f"Qualitative Data: {raw_sentiment}"
    )

    logger.info("Orchestrator analyzing swarm data for %s", active_ticker)
    logger.info("Pacing API request — waiting 3 seconds to avoid rate limits")
    await asyncio.sleep(3)

    try:
        decision: OrchestratorDirective = await _invoke_llm_with_backoff(
            structured_llm, system_prompt, analysis_context
        )

        if decision.action == "REJECT":
            final_action = "REJECT"
            final_shares = None
            final_allocation = None
        else:
            final_action = decision.action

            # Mutually exclusive: allocation vs shares to prevent API double-execution
            if requested_quantity is not None and float(requested_quantity) > 0:
                final_shares = float(requested_quantity)
                final_allocation = None
            else:
                final_shares = None
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
            else f"{final_allocation*100:.1f}% Allocation"
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
        }

    except Exception as e:
        err_msg = f"STATUS: ERROR - LLM Timeout/Rate Limit Exceeded: {str(e)}"
        logger.exception("Orchestrator LLM invocation failed for %s", active_ticker)
        return {
            "errors": [err_msg],
            "messages": [AIMessage(content=f"🚨 Orchestrator Error: {err_msg}")],
        }
