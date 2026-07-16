import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI # NEW IMPORT
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.state import FinancialSwarmState

# 1. The Strict Schema remains exactly the same
class TradeDecision(BaseModel):
    action: str = Field(description="Must be exactly 'BUY', 'SELL', or 'HOLD'")
    ticker: str = Field(description="The exact stock ticker symbol, e.g., 'AAPL'")
    shares: int = Field(description="Number of shares to trade (0 if HOLD)")
    reasoning: str = Field(description="A short, 2-sentence explanation of why this action was chosen based on the data.")

async def orchestrator_node(state: FinancialSwarmState) -> dict:
    """
    The True Brain. Passes the raw data to the Gemini LLM to reason over and 
    make a structured financial decision.
    """
    user_request = state["messages"][0].content if state["messages"] else "No request."
    quant_data = state.get("quant_data", {})
    sentiment_data = state.get("sentiment_data", {})

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
        "If the user asks you to buy on bullish sentiment, and the sentiment is indeed bullish, execute the trade. "
        "If data is missing or conflicting, default to HOLD."
    )
    
    analysis_context = (
        f"User Request: {user_request}\n\n"
        f"Quantitative Data from Quant Agent: {quant_data}\n\n"
        f"Qualitative Data from Sentiment Agent: {sentiment_data}"
    )

    print("\nGemini Orchestrator is analyzing the swarm data...")

    try:
        # 3. Invoke the Gemini LLM
        decision: TradeDecision = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_context)
        ])
        
        proposed_trade = {
            "ticker": decision.ticker,
            "action": decision.action,
            "shares": decision.shares,
            "estimated_price": 0.0 
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
        return {"errors": [f"Orchestrator LLM Failed: {str(e)}"]}
