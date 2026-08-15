from langgraph.graph import StateGraph, END
from src.state import FinancialSwarmState
from src.agents.parser_agent import parser_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.quant_agent import quant_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node
from src.agents.execution_agent import execution_agent_node


def route_after_orchestrator(state: FinancialSwarmState):
    proposed_trade = state.get("proposed_trade")

    # Safely extract action whether it's a model, dataclass, or dict
    if hasattr(proposed_trade, "action"):
        action = str(proposed_trade.action).upper()
    elif isinstance(proposed_trade, dict):
        action = str(proposed_trade.get("action", "HOLD")).upper()
    else:
        action = "HOLD"

    # Only halt if explicitly rejected
    if action == "REJECT":
        return END

    return "risk_agent_node"


def build_graph():
    """Constructs the LangGraph state machine. Returns an uncompiled builder
    so that callers (main.py) can attach checkpointers and interrupt points."""
    builder = StateGraph(FinancialSwarmState)

    builder.add_node("parser_node", parser_node)
    builder.add_node("sentiment_agent_node", sentiment_agent_node)
    builder.add_node("quant_agent_node", quant_agent_node)
    builder.add_node("orchestrator_node", orchestrator_node)
    builder.add_node("risk_agent_node", risk_agent_node)
    builder.add_node("execution_agent_node", execution_agent_node)

    builder.set_entry_point("parser_node")

    builder.add_edge("parser_node", "sentiment_agent_node")
    builder.add_edge("sentiment_agent_node", "quant_agent_node")
    builder.add_edge("quant_agent_node", "orchestrator_node")

    builder.add_conditional_edges(
        "orchestrator_node",
        route_after_orchestrator,
        {"risk_agent_node": "risk_agent_node", END: END},
    )

    builder.add_edge("risk_agent_node", "execution_agent_node")
    builder.add_edge("execution_agent_node", END)

    return builder
