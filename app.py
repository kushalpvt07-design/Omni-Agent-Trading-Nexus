import asyncio
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Import your existing agents
from src.state import FinancialSwarmState
from src.agents.quant_agent import quant_agent_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node
from src.agents.execution_agent import execution_agent_node

load_dotenv()

# --- Page Config ---
st.set_page_config(page_title="Omni-Agent Nexus", page_icon="📈", layout="wide")
st.title("⚡ Omni-Agent Trading Nexus")

# --- Sidebar: The Control Panel ---
with st.sidebar:
    st.header("⚙️ System Configuration")
    paper_trading_mode = st.toggle("Enable Live Paper Trading (Alpaca)", value=False)
    st.info("If disabled, trades route to the local JSON ledger.")
    
    st.divider()
    st.write("Session Memory ID:")
    thread_id = st.text_input("Thread ID", value="ui_session_001")

# --- Graph Initialization ---
def build_graph():
    workflow = StateGraph(FinancialSwarmState)
    workflow.add_node("quant_agent", quant_agent_node)
    workflow.add_node("sentiment_agent", sentiment_agent_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("risk_agent", risk_agent_node)
    workflow.add_node("execution_agent", execution_agent_node)
    
    workflow.add_edge(START, "quant_agent")
    workflow.add_edge(START, "sentiment_agent")
    workflow.add_edge("quant_agent", "orchestrator")
    workflow.add_edge("sentiment_agent", "orchestrator")
    workflow.add_edge("orchestrator", "risk_agent")
    workflow.add_edge("risk_agent", "execution_agent")
    workflow.add_edge("execution_agent", END)
    return workflow

# --- Main UI Logic ---
user_prompt = st.text_input("Enter your trading directive:", placeholder="e.g., MSFT is my target. Buy 5 shares if sentiment is bullish.")

if st.button("🚀 Deploy Swarm", type="primary"):
    if not user_prompt:
        st.warning("Please enter a directive.")
    else:
        with st.status("Initializing Autonomous Agents...", expanded=True) as status:
            async def run_swarm():
                workflow = build_graph()
                async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
                    # We interrupt BEFORE execution to ask for human approval on the UI
                    app = workflow.compile(checkpointer=checkpointer, interrupt_before=["execution_agent"])
                    
                    config = {"configurable": {"thread_id": thread_id}}
                    initial_state = {
                        "messages": [HumanMessage(content=user_prompt)],
                        "paper_trading_enabled": paper_trading_mode, # Pass the toggle state!
                        "quant_data": {}, "sentiment_data": {}, "proposed_trade": {},
                        "risk_approved": False, "errors": []
                    }
                    
                    st.write("📡 Gathering Quant & Sentiment Data...")
                    current_state = await app.ainvoke(initial_state, config)
                    return current_state, app, config
            
            # Run the async graph in Streamlit
            current_state, compiled_app, thread_config = asyncio.run(run_swarm())
            status.update(label="Analysis Complete. Awaiting Human Approval.", state="complete", expanded=False)

        # --- Display the Results ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Orchestrator Analysis")
            # The second to last message is the Orchestrator
            st.info(current_state["messages"][-2].content)
            
        with col2:
            st.subheader("Risk & Compliance")
            # The last message is the Risk Desk
            if current_state.get("risk_approved"):
                st.success(current_state["messages"][-1].content)
            else:
                st.error(current_state["messages"][-1].content)

        # --- Human Checkpoint Buttons ---
        st.divider()
        st.subheader("🛑 Human Approval Required")
        
        if current_state.get("proposed_trade", {}).get("action") == "HOLD":
            st.write("No execution required. System defaulted to HOLD.")
        else:
            execute_col, cancel_col = st.columns([1, 5])
            with execute_col:
                if st.button("✅ Execute Trade", type="primary"):
                    async def approve_trade():
                        async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
                            # Resume the graph by passing None
                            final_state = await compiled_app.ainvoke(None, thread_config)
                            return final_state
                    
                    with st.spinner("Routing order..."):
                        final = asyncio.run(approve_trade())
                        st.success(final["messages"][-1].content)
            with cancel_col:
                if st.button("❌ Cancel"):
                    st.warning("Trade Sequence Aborted.")
