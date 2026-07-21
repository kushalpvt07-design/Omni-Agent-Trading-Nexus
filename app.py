import asyncio
import streamlit as st
import plotly.graph_objects as go
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

# 1. Initialize Persistent UI States
if "swarm_deployed" not in st.session_state:
    st.session_state.swarm_deployed = False
if "latest_state" not in st.session_state:
    st.session_state.latest_state = None

st.title("⚡ Omni-Agent Trading Nexus")

# --- Sidebar: The Control Panel ---
with st.sidebar:
    st.header("⚙️ System Configuration")
    paper_trading_mode = st.toggle(
        "Enable Live Paper Trading (Alpaca)", 
        value=st.session_state.get("paper_trading_enabled", False),
        key="paper_trading_enabled"
    )
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

if st.button("🚀 Deploy Swarm", type="primary") or st.session_state.swarm_deployed:
    if not st.session_state.swarm_deployed:
        if not user_prompt:
            st.warning("Please enter a directive.")
        else:
            with st.status("🧬 Swarm Consensus Pipeline Active...", expanded=True) as status:
                st.write("🔍 **Quant Agent:** Fetching real-time order book and market indicators...")
                st.write("📊 **Sentiment Agent:** Parsing latest financial news feeds and social sentiment...")
                st.write("🛡️ **Risk Desk:** Verifying portfolio allocation limits...")

                async def run_swarm():
                    workflow = build_graph()
                    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
                        # We interrupt BEFORE execution to ask for human approval on the UI
                        app = workflow.compile(checkpointer=checkpointer, interrupt_before=["execution_agent"])
                        
                        config = {"configurable": {"thread_id": thread_id}}
                        initial_state = {
                            "messages": [HumanMessage(content=user_prompt)],
                            "paper_trading_enabled": st.session_state.paper_trading_enabled, # Pass the toggle state!
                            "quant_data": {}, "sentiment_data": {}, 
                            "current_ticker": "", # Initialize field
                            "proposed_trade": {},
                            "risk_approved": False, "errors": []
                        }
                        
                        current_state = await app.ainvoke(initial_state, config)
                        return current_state
                
                # Run the async graph in Streamlit
                current_state = asyncio.run(run_swarm())
                
                # Save to session state
                st.session_state.latest_state = current_state
                st.session_state.swarm_deployed = True
                status.update(label="Consensus Reached!", state="complete", expanded=False)

    # --- Render Output from Session State (Safe from Reruns) ---
    if st.session_state.swarm_deployed and st.session_state.latest_state:
        current_state = st.session_state.latest_state

        # --- Metrics Header ---
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            st.metric(label="Target Asset", value=current_state.get("current_ticker", "N/A"))
        with mcol2:
            action = current_state.get("proposed_trade", {}).get("action", "HOLD")
            st.metric(label="Swarm Signal", value=action, delta="BUY" if action == "BUY" else None)
        with mcol3:
            shares = current_state.get("proposed_trade", {}).get("shares", 0)
            st.metric(label="Order Size", value=f"{shares} Shares")
            
        st.divider()

        # --- Chart Visualization ---
        if "quant_data" in current_state:
            df = current_state["quant_data"].get("historical_df")
            if df is not None:
                st.subheader("📊 Market Data Analysis")
                fig = go.Figure(data=[go.Candlestick(
                    x=df['Date'],
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close']
                )])
                fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
                st.divider()
                
        # --- Results Columns ---
        col1, col2 = st.columns(2)
        
        with col1:
            # Inject custom CSS for custom glassmorphism style containers
            st.markdown("""
                <style>
                .trading-card {
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 10px;
                    padding: 20px;
                    border-left: 5px solid #00ffcc;
                    margin-bottom: 20px;
                }
                .reasoning-text {
                    font-family: 'Courier New', monospace;
                    color: #e0e0e0;
                }
                </style>
                """, unsafe_allow_html=True)
            
            # The second to last message is the Orchestrator
            reasoning = current_state["messages"][-2].content if len(current_state["messages"]) >= 2 else "No analysis provided."
            st.markdown(f"""
                <div class="trading-card">
                    <h3>🧠 Orchestrator Core Intelligence</h3>
                    <p class="reasoning-text">{reasoning}</p>
                </div>
                """, unsafe_allow_html=True)
            
        with col2:
            st.subheader("Risk & Compliance")
            # The last message is the Risk Desk
            if current_state.get("risk_approved"):
                st.success(current_state["messages"][-1].content)
            else:
                st.error(current_state["messages"][-1].content)

        # --- Human Checkpoint Buttons (Flat Execution Layer) ---
        st.divider()
        st.subheader("🛑 Human Approval Required")
        
        if current_state.get("proposed_trade", {}).get("action") == "HOLD":
            st.write("No execution required. System defaulted to HOLD.")
            if st.button("🔄 Reset"):
                st.session_state.swarm_deployed = False
                st.session_state.latest_state = None
                st.rerun()
        else:
            execute_col, cancel_col = st.columns([1, 5])
            with execute_col:
                if st.button("✅ Execute Trade", type="primary"):
                    async def approve_trade():
                        workflow = build_graph()
                        async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
                            app = workflow.compile(checkpointer=checkpointer, interrupt_before=["execution_agent"])
                            config = {"configurable": {"thread_id": thread_id}}
                            # Resume the graph by passing None
                            final_state = await app.ainvoke(None, config)
                            return final_state
                    
                    with st.spinner("Routing order..."):
                        final = asyncio.run(approve_trade())
                        st.success(final["messages"][-1].content)
                        st.session_state.swarm_deployed = False
                        st.session_state.latest_state = None
            with cancel_col:
                if st.button("❌ Cancel"):
                    st.warning("Trade Sequence Aborted.")
                    st.session_state.swarm_deployed = False
                    st.session_state.latest_state = None
                    st.rerun()
