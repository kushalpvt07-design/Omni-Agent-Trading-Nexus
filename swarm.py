from langgraph.graph import StateGraph, START, END
from src.state import FinancialSwarmState
from src.agents.quant_agent import quant_agent_node
from src.agents.sentiment_agent import sentiment_agent_node
from src.agents.orchestrator import orchestrator_node
from src.agents.risk_agent import risk_agent_node
from src.agents.execution_agent import execution_agent_node

from src.agents.parser_agent import parser_node

def build_graph():
    workflow = StateGraph(FinancialSwarmState)
    workflow.add_node("parser_node", parser_node)
    workflow.add_node("quant_agent", quant_agent_node)
    workflow.add_node("sentiment_agent", sentiment_agent_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("risk_agent", risk_agent_node)
    workflow.add_node("execution_agent", execution_agent_node)
    
    workflow.add_edge(START, "parser_node")
    workflow.add_edge("parser_node", "quant_agent")
    workflow.add_edge("parser_node", "sentiment_agent")
    workflow.add_edge("quant_agent", "orchestrator")
    workflow.add_edge("sentiment_agent", "orchestrator")
    workflow.add_edge("orchestrator", "risk_agent")
    workflow.add_edge("risk_agent", "execution_agent")
    workflow.add_edge("execution_agent", END)
    return workflow

# Compile the graph without checkpointer for the synchronous / stateless API endpoint
app = build_graph().compile()
