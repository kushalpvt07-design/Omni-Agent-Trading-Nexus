"""
src.agents — LangGraph agent node functions.

Each agent is an async function that receives FinancialSwarmState and returns
a partial state update dict. They are wired together in swarm.py via StateGraph.

Public API:
    parser_node           — Extracts structured trade parameters from NL
    sentiment_agent_node  — Fetches news sentiment via MCP
    quant_agent_node      — Retrieves technical indicators via MCP
    orchestrator_node     — Synthesizes data into BUY/SELL/HOLD/REJECT
    risk_agent_node       — Enforces position sizing and compliance
    execution_agent_node  — Submits orders to Alpaca, updates ledger
"""

from src.agents.parser_agent import parser_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.quant_agent import quant_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node
from src.agents.execution_agent import execution_agent_node

__all__ = [
    "parser_node",
    "sentiment_agent_node",
    "quant_agent_node",
    "orchestrator_node",
    "risk_agent_node",
    "execution_agent_node",
]
