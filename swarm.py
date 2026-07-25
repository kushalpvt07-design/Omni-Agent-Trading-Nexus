from langgraph.graph import StateGraph, END
from src.state import FinancialSwarmState
from src.agents.parser_agent import parser_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.quant_agent import quant_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node
from src.agents.execution_agent import execution_agent_node

def route_after_orchestrator(state: FinancialSwarmState):
    proposed_trade = state.get("proposed_trade", {})
    if not isinstance(proposed_trade, dict):
        proposed_trade = {}
        
    action = str(proposed_trade.get("action", "HOLD")).upper()
    shares = float(proposed_trade.get("shares", 0.0) or 0.0)
    allocation = float(proposed_trade.get("allocation", 0.0) or 0.0)
    
    # Halt graph on HOLD or REJECT
    if action in ["REJECT", "HOLD"] or (shares <= 0.0 and allocation <= 0.0):
        return END
    
    return "risk_agent"

def build_graph():
    builder = StateGraph(FinancialSwarmState)
    
    builder.add_node("parser_node", parser_node)
    builder.add_node("sentiment_agent", sentiment_agent_node)
    builder.add_node("quant_agent", quant_agent_node)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("risk_agent", risk_agent_node)
    builder.add_node("execution_agent", execution_agent_node)
    
    builder.set_entry_point("parser_node")
    
    builder.add_edge("parser_node", "sentiment_agent")
    builder.add_edge("sentiment_agent", "quant_agent")
    builder.add_edge("quant_agent", "orchestrator")
    
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "risk_agent": "risk_agent",
            END: END
        }
    )
    
    builder.add_edge("risk_agent", "execution_agent")
    builder.add_edge("execution_agent", END)
    
    return builder
