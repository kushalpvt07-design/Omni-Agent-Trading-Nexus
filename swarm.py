from langgraph.graph import StateGraph, START, END
from src.state import FinancialSwarmState
from src.agents.quant_agent import quant_agent_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node, pre_flight_risk_node
from src.agents.execution_agent import execution_agent_node

from src.agents.parser_agent import parser_node

def route_after_parser(state: FinancialSwarmState):
    if state.get("errors"):
        return END
    return "pre_flight_risk"

def route_after_pre_flight(state: FinancialSwarmState):
    if state.get("errors"):
        return END
    # Correct parallel routing in LangGraph
    return ["quant_agent", "sentiment_agent"]

def build_graph():
    workflow = StateGraph(FinancialSwarmState)
    workflow.add_node("parser_node", parser_node)
    workflow.add_node("pre_flight_risk", pre_flight_risk_node)
    workflow.add_node("quant_agent", quant_agent_node)
    workflow.add_node("sentiment_agent", sentiment_agent_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("risk_agent", risk_agent_node)
    workflow.add_node("execution_agent", execution_agent_node)
    
    workflow.add_edge(START, "parser_node")
    workflow.add_conditional_edges("parser_node", route_after_parser, {END: END, "pre_flight_risk": "pre_flight_risk"})
    
    # Send the output of pre_flight to BOTH parallel nodes or kill the graph
    workflow.add_conditional_edges("pre_flight_risk", route_after_pre_flight)
    
    workflow.add_edge(["quant_agent", "sentiment_agent"], "orchestrator")
    workflow.add_edge("orchestrator", "risk_agent")
    workflow.add_edge("risk_agent", "execution_agent")
    workflow.add_edge("execution_agent", END)
    return workflow

# Compile the graph without checkpointer for the synchronous / stateless API endpoint
app = build_graph().compile()
