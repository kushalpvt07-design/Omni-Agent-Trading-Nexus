from langgraph.graph import StateGraph, END
from src.state import FinancialSwarmState
from src.agents.parser_agent import parser_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.quant_agent import quant_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node
from src.agents.execution_agent import execution_agent_node


def route_after_parser(state: FinancialSwarmState):
    """Fan out to both Sentiment and Quant agents in parallel if parsing succeeded;
    route directly to orchestrator_node (which formats the rejection message) if errors occurred."""
    if state.get("errors") or not state.get("current_ticker") or state.get("current_ticker") == "UNKNOWN":
        return ["orchestrator_node"]
    return ["sentiment_agent_node", "quant_agent_node"]


def route_after_orchestrator(state: FinancialSwarmState):
    proposed_trade = state.get("proposed_trade")

    if hasattr(proposed_trade, "action"):
        action = str(proposed_trade.action).upper()
    elif isinstance(proposed_trade, dict):
        action = str(proposed_trade.get("action", "HOLD")).upper()
    else:
        action = "HOLD"

    if action == "REJECT":
        return END

    return "risk_agent_node"


def route_after_risk(state: FinancialSwarmState):
    """Only send to the HITL execution checkpoint when risk approved
    a real BUY or SELL order. HOLDs and risk-rejected overrides skip straight
    to END so they never show the human-approval modal.
    """
    if not state.get("risk_approved", False):
        return END

    proposed_trade = state.get("proposed_trade", {})
    action = ""
    if hasattr(proposed_trade, "action"):
        action = str(proposed_trade.action).upper()
    elif isinstance(proposed_trade, dict):
        action = str(proposed_trade.get("action", "")).upper()

    if action not in ("BUY", "SELL"):
        return END

    return "execution_agent_node"


def build_graph():
    """Constructs the LangGraph state machine with parallel Quant + Sentiment fan-out/fan-in."""
    builder = StateGraph(FinancialSwarmState)

    builder.add_node("parser_node", parser_node)
    builder.add_node("sentiment_agent_node", sentiment_agent_node)
    builder.add_node("quant_agent_node", quant_agent_node)
    builder.add_node("orchestrator_node", orchestrator_node)
    builder.add_node("risk_agent_node", risk_agent_node)
    builder.add_node("execution_agent_node", execution_agent_node)

    builder.set_entry_point("parser_node")

    # Parallel fan-out from parser_node to sentiment_agent_node and quant_agent_node
    builder.add_conditional_edges(
        "parser_node",
        route_after_parser,
        ["sentiment_agent_node", "quant_agent_node", "orchestrator_node"],
    )

    # Fan-in synchronization barrier: wait for both parallel branches before orchestrator_node
    builder.add_edge(["sentiment_agent_node", "quant_agent_node"], "orchestrator_node")

    builder.add_conditional_edges(
        "orchestrator_node",
        route_after_orchestrator,
        {"risk_agent_node": "risk_agent_node", END: END},
    )

    builder.add_conditional_edges(
        "risk_agent_node",
        route_after_risk,
        {"execution_agent_node": "execution_agent_node", END: END},
    )
    builder.add_edge("execution_agent_node", END)

    return builder
