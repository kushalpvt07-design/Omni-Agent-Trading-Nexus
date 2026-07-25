import streamlit as st
import requests

st.set_page_config(page_title="Trading Nexus", layout="wide")
st.title("⚡ Omni-Agent Trading Nexus")

directive = st.text_input("Enter your trading directive:", placeholder="Evaluate buying 10 shares of AAPL")
paper_trading = st.toggle("Enable Live Paper Trading (Alpaca)", value=True)

if st.button("Deploy Swarm"):
    if not directive:
        st.error("Enter a directive before deploying the swarm.")
    else:
        with st.spinner("🧬 Swarm Consensus Pipeline Active..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/api/v1/analyze", 
                    json={"directive": directive, "paper_trading": paper_trading},
                    timeout=300 
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "ERROR":
                        st.error(f"🚨 CRITICAL SYSTEM FAILURE: {data.get('error_message', 'Unknown Error')}")
                    else:
                        action = data.get("action", "HOLD")
                        
                        if action in ["BUY", "SELL"]:
                            st.success(f"Swarm Consensus Reached: {action} Proposed")
                        else:
                            st.warning(f"Swarm Consensus Reached: Position set to {action}")
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Target Asset", data.get("ticker", "N/A"))
                        col2.metric("Swarm Signal", action)
                        
                        # FIX: Bulletproof frontend string/null coercion
                        raw_shares = data.get("shares")
                        try:
                            shares_val = float(raw_shares) if raw_shares is not None else 0.0
                        except (ValueError, TypeError):
                            shares_val = 0.0
                            
                        col3.metric("Order Size", f"{int(shares_val)} Shares" if shares_val % 1 == 0 else f"{shares_val:.4f} Shares")
                        
                        reasoning = data.get("orchestrator_reasoning", "No detailed reasoning provided by the swarm.")
                        st.info(f"**Orchestrator Reasoning:** {reasoning}")
                else:
                    st.error(f"Backend Server Error ({response.status_code}): {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("CRITICAL FAILURE: Cannot connect to FastAPI backend. Is Uvicorn actually running?")
            except requests.exceptions.Timeout:
                st.error("TIMEOUT: The swarm took too long to reach consensus. Check LLM API rate limits.")
