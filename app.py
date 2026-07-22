import streamlit as st
import requests

st.set_page_config(page_title="Trading Nexus", layout="wide")
st.title("⚡ Omni-Agent Trading Nexus")

# Input for the swarm
directive = st.text_input("Enter your trading directive:", placeholder="Evaluate buying 10 shares of AAPL")
paper_trading = st.toggle("Enable Live Paper Trading (Alpaca)", value=True)

if st.button("Deploy Swarm"):
    if not directive:
        st.error("Enter a directive before deploying the swarm.")
    else:
        with st.spinner("🧬 Swarm Consensus Pipeline Active..."):
            try:
                # Fire the request to your FastAPI backend
                response = requests.post(
                    "http://127.0.0.1:8000/api/v1/analyze", 
                    json={"directive": directive, "paper_trading": paper_trading},
                    timeout=120 # Give the poor LLMs a fighting chance (120 seconds)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "ERROR":
                        st.error(f"🚨 CRITICAL SYSTEM FAILURE: {data.get('error_message')}")
                    else:
                        # Display the results
                        st.success("Swarm Consensus Reached")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Target Asset", data["ticker"])
                    col2.metric("Swarm Signal", data["action"])
                    col3.metric("Order Size", f"{data['shares']} Shares")
                    
                    st.info(f"**Orchestrator Reasoning:** {data['orchestrator_reasoning']}")
                else:
                    st.error(f"Backend Server Error: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("CRITICAL FAILURE: Cannot connect to FastAPI backend. Is Uvicorn actually running?")
