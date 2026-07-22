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
    shares: int = Field(description="Number of shares to trade (0 if HOLD)")
    reasoning: str = Field(description="A short, 2-sentence explanation of why this action was chosen based on the data.")

@retry(
    retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted),
    wait=wait_exponential_jitter(initial=1, max=60, exp_base=2, jitter=1),
    stop=stop_after_attempt(5)
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

    # 2. Initialize the Gemini Model with a robust fallback list
    models_to_try = [
        "gemini-3.5-flash",
        "gemini-3-flash",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-live",
        "gemini-flash-latest",
        "gemini-2.5-flash"
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
        "CRITICAL RULE: If the quantitative data indicates that the target ticker is missing, delisted, invalid, or DATA_CORRUPT, you MUST reject the trade. Set the action to 'HOLD', shares to 0, and state this failure in your reasoning, completely ignoring any bullish sentiment data. "
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
        
        proposed_trade = {
            "ticker": decision.ticker,
            "action": decision.action,
            "shares": decision.shares,
            "estimated_price": 0.0,
            "reasoning": decision.reasoning
        }
        
        final_report = (
            f"**AI Swarm Analysis Complete for {decision.ticker}**\n\n"
            f"**Action:** {decision.action} {decision.shares} Shares\n"
            f"**Reasoning:** {decision.reasoning}"
        )
        
        return {
            "proposed_trade": proposed_trade,
            "messages": [AIMessage(content=final_report)]
        }
        
    except Exception as e:
        return {"errors": ["STATUS: ERROR - LLM Timeout/Rate Limit Exceeded. Validation failed after retries."]}
