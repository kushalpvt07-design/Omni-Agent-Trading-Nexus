import asyncio
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.state import FinancialSwarmState
from src.agents.quant_agent import quant_agent_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node # NEW: Import the Risk Desk
from src.agents.execution_agent import execution_agent_node

from src.agents.parser_agent import parser_node

workflow = StateGraph(FinancialSwarmState)

workflow.add_node("parser_agent", parser_node)
workflow.add_node("quant_agent", quant_agent_node)
workflow.add_node("sentiment_agent", sentiment_agent_node)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("risk_agent", risk_agent_node) # NEW: Register the node
workflow.add_node("execution_agent", execution_agent_node)

workflow.add_edge(START, "parser_agent")
workflow.add_edge("parser_agent", "quant_agent")
workflow.add_edge("parser_agent", "sentiment_agent")
workflow.add_edge("quant_agent", "orchestrator")
workflow.add_edge("sentiment_agent", "orchestrator")

# NEW ROUTING LOGIC: Orchestrator -> Risk -> Execution
workflow.add_edge("orchestrator", "risk_agent")
workflow.add_edge("risk_agent", "execution_agent")
workflow.add_edge("execution_agent", END)

async def run_pipeline():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        app = workflow.compile(
            checkpointer=checkpointer, 
            interrupt_before=["execution_agent"] # Keep the human gate exactly here
        )
        
        # Bump the thread ID to avoid caching the previous runs
        thread_config = {"configurable": {"thread_id": "live_trade_session_009"}}
        
        # I aggressively increased the requested shares to trigger the risk limit
        initial_state = {
            "messages": [HumanMessage(content="MSFT is my target. Buy 10 shares if the news is good.")],
            "quant_data": {},
            "sentiment_data": {},
            "proposed_trade": {},
            "risk_approved": False,
            "errors": []
        }
        
        print("🚀 Launching Omni-Agent Trading Nexus...")
        current_state = await app.ainvoke(initial_state, thread_config)
        
        print("\n================================================")
        print("🛑 HUMAN IN THE LOOP REQUIRED 🛑")
        print("================================================\n")
        
        if current_state.get("errors"):
            print("⚠️ SYSTEM ERRORS DETECTED:")
            for err in current_state["errors"]:
                print(f" - {err}")
            print("\n")
            
        # Print the last TWO messages so you can see both Orchestrator AND Risk output
        for msg in current_state["messages"][-2:]:
            print(msg.content)
            print("-" * 40)
            
        print("\nProposed Trade (Post-Risk):", current_state.get("proposed_trade"))
        
        user_input = input("\nType 'y' to approve execution ledger update, or 'n' to drop: ")
        
        if user_input.lower() == 'y':
            final_state = await app.ainvoke(None, thread_config)
            print("\n================================================")
            print(final_state["messages"][-1].content)
            print("================================================")
        else:
            print("\nTrade sequence terminated by user.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
