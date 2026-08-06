# 📈 Omni-Agent Trading Nexus: Autonomous Swarm Execution

## 📌 The Problem
Standard retail trading algorithms are completely blind to qualitative market shifts, while naïve single-agent LLM wrappers will happily hallucinate a "BUY" order on a delisted ticker and liquidate an entire portfolio. Financial systems lack the asynchronous, multi-threaded intelligence required to merge hard quantitative data with real-time sentiment without collapsing under API rate limits or state-wiping data collisions.

## 🛡️ The Solution
This repository implements an autonomous, multi-agent financial swarm. Driven by a deterministic LangGraph state machine, it partitions cognitive load across specialized AI nodes. Distinct agents handle natural language parsing, quantitative technical analysis, and sentiment extraction asynchronously. Crucially, the system enforces a strict Human-in-the-Loop (HITL) execution breakpoint, physically preventing the AI from firing live orders to the brokerage without manual authorization.

## ⚙️ Key Architecture Components
* **Stateful Swarm Memory:** Bypasses standard data collisions using custom `operator.add` and `merge_dicts` reducers in the graph state. This allows the Quant and Sentiment agents to compile a massive, unified JSON context payload simultaneously without overwriting each other's data.
* **Pydantic Execution Guardrails:** The Orchestrator node does not guess. It is forcefully constrained by a strictly typed `TradeProposal` schema. If market volume reads zero or upstream analytical nodes crash, the LLM is hard-coded to override the user's initial request and aggressively output a "REJECT" directive.
* **Resilient Orchestration:** API rate limits destroy standard AI pipelines. The core Gemini inference engine utilizes intelligent model cascading (defaulting to `gemini-3.6-flash`) wrapped in aggressive exponential backoff, ensuring the swarm survives HTTP 429 throttling without dropping the graph state.
* **Asynchronous UI Streaming:** A React/TypeScript frontend utilizing a custom `useSwarmWebSocket.ts` hook. It intercepts live LangGraph state mutations and instantly maps the AI's internal reasoning, error logs, and execution proposals directly to the dashboard.

## 🧠 Tech Stack
* **Frontend:** React, TypeScript, TailwindCSS
* **Backend / API Gateway:** Python 3, FastAPI, WebSockets
* **AI Orchestration:** LangGraph, LangChain Core
* **Data Validation & Resiliency:** Pydantic, Tenacity
* **Inference Engine:** Google Gemini API (Model Cascading Enabled)

## 🚀 Quick Start
This system operates with a decoupled architecture. You must run the FastAPI swarm and the React frontend concurrently.

### 1. Initialize the AI Swarm (Backend)
Navigate to the backend directory and spin up the asynchronous LangGraph environment.

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure Environment Variables
Create a .env file in the backend root. Do not commit your API keys.

```bash
GEMINI_API_KEY="your_google_api_key_here"
ALPACA_API_KEY="your_broker_key"
ALPACA_SECRET_KEY="your_broker_secret"
```

## 3. Launch the Orchestrator

```bash
uvicorn main:app --reload --port 8000
```
The WebSocket stream will be available at ws://localhost:8000/ws

## 🧪 API Usage & Testing
The system is designed to gracefully handle adversarial inputs and market anomalies.

### Test Case 1: The Delisted Asset / Corrupted Data
* **State:** User attempts to force a massive buy order on a ticker with 0 volume.
* **Expected Result:** The Quant agent flags the missing volume in the graph state. The Orchestrator node reads the state, triggers the critical override rule, and forcefully changes the action to "REJECT". `final_shares` and `final_allocation` are zeroed out. The broker API is never touched.

### Test Case 2: The HITL Breakpoint
* **State:** User requests a 10% portfolio allocation on a valid, high-momentum ticker.
* **Expected Result:** The AI swarm successfully merges sentiment and quant data, calculating the exact estimated price and reasoning. The LangGraph pauses execution. The UI displays the `TradeProposal`. The system remains idle until a human operator toggles the `human_approved` boolean flag to `true`, at which point the final broker execution node fires.
