import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.state import FinancialSwarmState
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
import google.api_core.exceptions

# 1. The Strict Schema remains exactly the same
class TradeDecision(BaseModel):
    action: str = Field(description="Must be exactly 'BUY', 'SELL', or 'HOLD'")
    ticker: str = Field(description="The exact stock ticker symbol, e.g., 'AAPL'")
    allocation: float = Field(description="Target percentage as a strict decimal between 0.0 and 1.0 (e.g., 18% is 0.18). NEVER output > 1.0.")
    reasoning: str = Field(description="A 2-sentence explanation of the market data. DO NOT calculate shares, do not mention portfolio cash, and do not output position sizes. NO MATH.")

@retry(
    retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted),
    wait=wait_exponential_jitter(initial=1, max=15, exp_base=2, jitter=1), # Cap the wait at 15s, not 60s
    stop=stop_after_attempt(4) # Kill it faster if the API is truly dead
)
async def _invoke_llm_with_backoff(structured_llm, system_prompt, analysis_context):
    return await structured_llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=analysis_context)
    ])

async def orchestrator_node(state: FinancialSwarmState) -> dict:
    """
    The True Brain. Passes the raw data to the Gemini LLM to reason over and 
    make a structured financial decision.
    """
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
    requested_allocation = state.get("requested_allocation")


    models_to_try = [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-3-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-tts",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.1-flash-tts",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    
    primary_llm = ChatGoogleGenerativeAI(model=models_to_try[0], temperature=0.0)
    structured_llm = primary_llm.with_structured_output(TradeDecision)
    
    fallbacks = [
        ChatGoogleGenerativeAI(model=m, temperature=0.0).with_structured_output(TradeDecision)
        for m in models_to_try[1:]
    ]
    
    structured_llm = structured_llm.with_fallbacks(fallbacks)

    system_prompt = (
        "You are an elite autonomous financial orchestrator. "
        "Analyze the provided quantitative data and qualitative market sentiment. "
        "Your job is to synthesize this data and make a final trading decision. "
        "Do not calculate shares. Only output the target portfolio allocation percentage as a float between 0.0 and 1.0. "
        "CRITICAL RULE: If the quantitative data indicates that the target ticker is missing, delisted, invalid, or DATA_CORRUPT, you MUST reject the trade. Set the action to 'HOLD', allocation to 0.0, and state this failure in your reasoning, completely ignoring any bullish sentiment data. "
        "If the data is valid and indicates bullish patterns or confirmations matching the user request, authorize the trade."
    )
    
    analysis_context = (
        f"User Request: {user_request}\n\n"
        f"Target Ticker: {active_ticker}\n\n"
        f"Quantitative Data: {raw_quant}\n\n"
        f"Qualitative Data: {raw_sentiment}"
    )

    print("\nGemini Orchestrator is analyzing the swarm data...")

    try:
        # 3. Invoke the Gemini LLM with exponential backoff
        decision: TradeDecision = await _invoke_llm_with_backoff(structured_llm, system_prompt, analysis_context)
        
        final_action = requested_action if requested_action else decision.action
        final_allocation = float(requested_allocation) if requested_allocation is not None else decision.allocation
        final_shares = float(requested_quantity) if requested_quantity is not None else 0.0

        proposed_trade = {
            "ticker": active_ticker, # HARD OVERRIDE: Use state ticker (ETH/USD), not decision.ticker (ETH)
            "action": final_action,
            "allocation": 0.0 if final_shares > 0 else final_allocation,
            "shares": final_shares,
            "estimated_price": 0.0,
            "reasoning": decision.reasoning
        }
        
        report_qty = f"{final_shares} Shares" if final_shares > 0 else f"{final_allocation*100:.1f}% Allocation"
        
        final_report = (
            f"**AI Swarm Analysis Complete for {decision.ticker}**\n\n"
            f"**Action:** {final_action} {report_qty}\n"
            f"**Reasoning:** {decision.reasoning}"
        )
        
        return {
            "proposed_trade": proposed_trade,
            "messages": [AIMessage(content=final_report)]
        }
        
    except Exception as e:
        return {"errors": ["STATUS: ERROR - LLM Timeout/Rate Limit Exceeded. Validation failed after retries."]}
