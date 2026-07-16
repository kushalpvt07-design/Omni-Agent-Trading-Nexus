import asyncio
from src.state import FinancialSwarmState
from langchain_core.messages import HumanMessage
from src.agents.quant_agent import quant_agent_node
from src.agents.sentiment_agent import sentiment_agent_node

async def main():
    state = FinancialSwarmState(
        messages=[HumanMessage(content="Buy the tesla 1000 shares")],
        paper_trading_enabled=False,
        quant_data={},
        sentiment_data={},
        proposed_trade={},
        risk_approved=False,
        errors=[]
    )
    result = await quant_agent_node(state)
    print("QUANT RESULT:", result)
    result_s = await sentiment_agent_node(state)
    print("SENTIMENT RESULT:", result_s)

asyncio.run(main())
