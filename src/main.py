import asyncio
import sqlite3
from dotenv import load_dotenv
load_dotenv()
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver # The Brakes

from src.state import FinancialSwarmState
from src.agents.quant_agent import quant_agent_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.orchestrator import orchestrator_node

# --- NEW: The Execution Node ---
# This is the node we will protect with our Human-in-the-Loop check.
async def execution_node(state: FinancialSwarmState) -> dict:
    trade = state.get("proposed_trade", {})
    if not trade or trade.get("action") == "HOLD":
        return {"messages": [AIMessage(content="Execution: No trade required. Holding position.")]}
    
    return {"messages": [AIMessage(content=f"Execution: SUCCESS. Executed {trade['action']} for {trade.get('shares', 0)} shares of {trade.get('ticker')}.")]}

# 1. Initialize the StateGraph
workflow = StateGraph(FinancialSwarmState)

# 2. Register all nodes
workflow.add_node("quant_agent", quant_agent_node)
workflow.add_node("sentiment_agent", sentiment_agent_node)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("execution_agent", execution_node) # NEW

# 3. Define the Control Flow
workflow.add_edge(START, "quant_agent")
workflow.add_edge(START, "sentiment_agent")
workflow.add_edge("quant_agent", "orchestrator")
workflow.add_edge("sentiment_agent", "orchestrator")
workflow.add_edge("orchestrator", "execution_agent") # Route to execution
workflow.add_edge("execution_agent", END)

async def run_pipeline():
    # 4. Connect the SQLite Database (The Checkpointer)
    # We use an async connection to safely handle the graph's state memory
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        
        # 5. Compile with the safety brakes ON
        # interrupt_before means it will freeze *exactly* before the execution_agent runs.
        app = workflow.compile(
            checkpointer=checkpointer, 
            interrupt_before=["execution_agent"]
        )
        
        # To use memory, we MUST give this run a unique Thread ID
        thread_config = {"configurable": {"thread_id": "trade_session_001"}}
        
        initial_state = {
            "messages": [HumanMessage(content="Analyze AAPL. If sentiment is bullish, buy 50 shares.")],
            "quant_data": {},
            "sentiment_data": {},
            "proposed_trade": {},
            "risk_approved": False,
            "errors": []
        }
        
        print("Launching Omni-Agent Trading Nexus...")
        print("Gathering data and drafting proposal...")
        
        # Run the graph. It will hit the Orchestrator, then FREEZE.
        current_state = await app.ainvoke(initial_state, thread_config)
        
        print("\n================================================")
        print("HUMAN IN THE LOOP REQUIRED")
        print("================================================\n")
        
        # Pull the latest message (the Orchestrator's report)
        print(current_state["messages"][-1].content)
        print("\nProposed Trade:", current_state.get("proposed_trade"))
        
        # 6. The Human Approval Gate
        user_input = input("\nType 'y' to approve and execute, or 'n' to cancel: ")
        
        if user_input.lower() == 'y':
            print("\nExecuting trade...")
            # RESUME THE GRAPH: Passing 'None' as input tells it to just pick up where it left off
            final_state = await app.ainvoke(None, thread_config)
            print("\nFinal Status:")
            print(final_state["messages"][-1].content)
        else:
            print("\nTrade cancelled by user. Graph execution aborted.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
