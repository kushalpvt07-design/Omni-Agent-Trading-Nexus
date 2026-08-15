# Omni-Agent Trading Nexus

> **Autonomous multi-agent financial analysis and execution system** powered by a LangGraph swarm of specialized AI agents, Model Context Protocol (MCP) data servers, and a real-time Next.js command dashboard.

[![License](https://img.shields.io/badge/License-Apache_2.0-teal.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Next.js Dashboard (UI)                     │
│  SwarmDirectiveInput → AssetIntelligence → SwarmConsensus       │
│  MarketPulse → NexusPipelineLog → HumanInTheLoopModal           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ WebSocket (ws://localhost:8000)
┌──────────────────────▼──────────────────────────────────────────┐
│                     FastAPI Backend (main.py)                    │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Parser   │→│ Sentiment │→│  Quant   │→│ Orchestrator  │  │
│  │  Agent    │  │  Agent    │  │  Agent   │  │    Agent      │  │
│  └──────────┘  └─────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│                      │ MCP          │ MCP           │           │
│               ┌──────▼──────┐ ┌────▼────┐  ┌───────▼────────┐ │
│               │  Sentiment  │ │  Quant  │  │   Risk Agent   │ │
│               │   Server    │ │  Server │  │  (Compliance)  │ │
│               └─────────────┘ └─────────┘  └───────┬────────┘ │
│                                                     │          │
│                                            ┌────────▼────────┐ │
│                                            │ Execution Agent │ │
│                                            │  (Alpaca API)   │ │
│                                            └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Pipeline

| Agent | Responsibility |
|-------|---------------|
| **Parser Agent** | Extracts structured trade parameters (ticker, action, quantity) from natural language using Gemini |
| **Sentiment Agent** | Fetches real-time news headlines via MCP → yfinance and analyzes market sentiment |
| **Quant Agent** | Retrieves historical price data, volatility metrics, and technical indicators via MCP → Alpaca |
| **Orchestrator Agent** | Synthesizes all data streams into a final BUY/SELL/HOLD/REJECT decision |
| **Risk Agent** | Enforces position sizing, volatility limits, overdraft guards, and naked-short prohibition |
| **Execution Agent** | Submits orders to Alpaca (paper or live), updates the portfolio ledger |

### Safety Features

- **Human-in-the-Loop (HITL):** Every trade pauses at a checkpoint for explicit user approval before execution
- **Paper Trading Mode:** Enabled by default — no real money at risk
- **Risk Desk Compliance:** Dynamic position sizing based on 30-day volatility, overdraft prevention, naked-short blocking
- **Input Sanitization:** User directives are cleaned, truncated, and injection-protected before reaching any LLM
- **API Authentication:** All REST and WebSocket endpoints are protected via `X-API-Key` and `token` parameters.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini (via LangChain) |
| Agent Orchestration | LangGraph (StateGraph with checkpointing) |
| Data Servers | Model Context Protocol (MCP) |
| Trading API | Alpaca Markets |
| Backend | FastAPI + WebSockets |
| Frontend | Next.js 16 + React 19 + Recharts + Tailwind CSS 4 |
| State Persistence | SQLite (LangGraph checkpoints) |

---

## Prerequisites

- **Python 3.12+**
- **Node.js 22+** and npm
- API keys for:
  - [Google AI Studio](https://aistudio.google.com/apikey) (Gemini)
  - [Alpaca Markets](https://app.alpaca.markets/signup) (Paper trading)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/kushalpvt07-design/Omni-Agent-Trading-Nexus.git
cd Omni-Agent-Trading-Nexus
```

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd omni-nexus-ui
npm install
cd ..
```

### 4. Environment Variables

```bash
cp .env.example .env
# Edit .env with your real API keys and generated NEXUS_API_SECRET

# Set up the frontend auth token
cd omni-nexus-ui
echo "NEXT_PUBLIC_NEXUS_API_SECRET=your_nexus_api_secret_here" > .env.local
cd ..
```

---

## Running the Application

### Start the Backend (Terminal 1)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend (Terminal 2)

```bash
cd omni-nexus-ui
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Project Structure

```
Omni-Agent-Trading-Nexus/
├── main.py                         # FastAPI entrypoint (Thin composition root)
├── swarm.py                        # LangGraph state machine definition
├── schemas.py                      # Pydantic request/response models
├── utils.py                        # Live asset data utilities (yfinance)
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
│
├── src/
│   ├── state.py                    # FinancialSwarmState TypedDict
│   ├── core/                       # Settings, logging, security
│   ├── api/                        # FastAPI routes & middleware
│   ├── persistence/                # SQLite checkpoint management
│   ├── agents/                     # LangGraph agent nodes
│   │   ├── parser_agent.py         # NLP entity extraction
│   │   ├── sentiment_agent.py      # News sentiment via MCP
│   │   ├── quant_agent.py          # Technical analysis via MCP
│   │   ├── orchestrator.py         # Decision synthesis (Gemini)
│   │   ├── risk_agent.py           # Compliance & risk management
│   │   └── execution_agent.py      # Alpaca order execution
│   └── servers/                    # Standalone MCP servers
│       ├── quant_server.py         # MCP server for Alpaca market data
│       └── sentiment_server.py     # MCP server for yfinance news
│
├── omni-nexus-ui/                  # Next.js 16 dashboard
│   ├── .env.local                  # Frontend environment variables
│   └── src/
│       ├── app/                    # Next.js App Router (page.tsx, layout.tsx)
│       ├── components/             # React UI Components
│       ├── hooks/                  # Custom React hooks (useSwarmWebSocket)
│       ├── types/                  # Shared TypeScript interfaces
│       └── lib/                    # REST API utilities
│
├── .github/workflows/ci.yml       # CI pipeline
└── LICENSE                         # Apache 2.0
```

---

## API Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| `GET` | `/health` | No | Health check for monitoring |
| `POST` | `/api/v1/analyze` | Yes | Stateless single-shot trade analysis |
| `WS` | `/api/v1/swarm-stream` | Yes | Real-time streaming swarm pipeline with HITL |

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
