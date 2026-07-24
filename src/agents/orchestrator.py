import os
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.state import FinancialSwarmState
from tenacity import retry, stop_after_attempt, wait_exponential
import google.api_core.exceptions

class OrchestratorDirective(BaseModel):
    action: Literal["BUY", "SELL", "HOLD", "REJECT"] = Field(...)
    shares: float = Field(..., description="Number of shares. MUST be 0.0 if Action is REJECT.")
    reasoning: str

    @model_validator(mode='after')
    def enforce_consistency(self):
        if self.action == "REJECT" and self.shares > 0:
            self.shares = 0.0
        elif self.shares <= 0.0 and self.action != "HOLD":
            self.action = "REJECT"
            self.shares = 0.0
        return self

@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=2, min=4, max=30)
)
async def _invoke_llm_with_backoff(structured_llm, system_prompt, analysis_context):
    return await structured_llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=analysis_context)
    ])

async def orchestrator_node(state: FinancialSwarmState) -> dict:
    if state.get("errors"):
        return {"messages": [AIMessage(content="🚨 Orchestrator skipped due to upstream errors.")]}
        
    user_request = "No request."
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            user_request = msg.content
            break
            
    active_ticker = state.get("current_ticker", "UNKNOWN")
    raw_quant = state.get("quant_data", {}).get(active_ticker, "No data available.")
    raw_sentiment = state.get("sentiment_data", {}).get(active_ticker, "No data available.")
    
    requested_action = state.get("requested_action", "BUY")
    requested_quantity = state.get("requested_quantity")
    
    # FIXED: Provide a default 10% allocation if none is requested so Risk Desk evaluates properly
    raw_alloc = state.get("requested_allocation")
    requested_allocation = float(raw_alloc) if raw_alloc is not None else 0.1

    # FIXED: Only valid models
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash"
    ]
    
    primary_llm = ChatGoogleGenerativeAI(model=models_to_try[0], temperature=0.0)
    structured_llm = primary_llm.with_structured_output(OrchestratorDirective)
    
    fallbacks = [
        ChatGoogleGenerativeAI(model=m, temperature=0.0).with_structured_output(OrchestratorDirective)
        for m in models_to_try[1:]
    ]
    
    structured_llm = structured_llm.with_fallbacks(fallbacks)

    system_prompt = (
        "You are an elite autonomous financial orchestrator. "
        "Analyze the provided quantitative data and qualitative market sentiment to make a final trading decision. "
        "CRITICAL RULE: If the quantitative data is missing, corrupted, or shows 0 volume, you MUST output action='REJECT' and shares=0.0. "
        "Under NO circumstances should you output a 'BUY' or 'SELL' action if valid market data is missing."
    )
    
    analysis_context = (
        f"User Request: {user_request}\n\n"
        f"Target Ticker: {active_ticker}\n\n"
        f"Quantitative Data: {raw_quant}\n\n"
        f"Qualitative Data: {raw_sentiment}"
    )

    print("\nGemini Orchestrator is analyzing the swarm data...")
    import asyncio
    print("[SYSTEM STATUS]: Pacing API to avoid rate limit death. Breathing for 3 seconds...")
    await asyncio.sleep(3)

    try:
        decision: OrchestratorDirective = await _invoke_llm_with_backoff(structured_llm, system_prompt, analysis_context)
        
        if decision.action == "REJECT" or decision.shares == 0.0:
            final_action = "REJECT"
            final_shares = 0.0
            final_allocation = 0.0
        else:
            final_action = requested_action if requested_action else decision.action
            final_shares = float(requested_quantity) if requested_quantity is not None else decision.shares
            final_allocation = requested_allocation

        # FIXED: Pass final_allocation instead of hardcoding 0.0
        proposed_trade = {
            "ticker": active_ticker,
            "action": final_action,
            "allocation": final_allocation,
            "shares": final_shares,
            "estimated_price": 0.0,
            "reasoning": decision.reasoning
        }
        
        report_qty = f"{final_shares} Shares" if final_shares > 0 else ""
        
        final_report = (
            f"**AI Swarm Analysis Complete for {active_ticker}**\n\n"
            f"**Action:** {final_action} {report_qty}\n"
            f"**Reasoning:** {decision.reasoning}"
        )
        
        return {
            "proposed_trade": proposed_trade,
            "messages": [AIMessage(content=final_report)]
        }
        
    except Exception as e:
        err_msg = f"STATUS: ERROR - LLM Timeout/Rate Limit Exceeded: {str(e)}"
        return {
            "errors": [err_msg],
            "messages": [AIMessage(content=f"🚨 Orchestrator Error: {err_msg}")]
        }
