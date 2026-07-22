from typing import TypedDict, Annotated, List, Dict, Any
import operator
from langchain_core.messages import BaseMessage

# Reducer function to safely merge dictionaries instead of overwriting them
def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {**(a or {}), **(b or {})}

class FinancialSwarmState(TypedDict):
    # operator.add ensures new messages/errors are appended to the list
    messages: Annotated[List[BaseMessage], operator.add]
    errors: Annotated[List[str], operator.add]
    
    # merge_dicts ensures parallel updates don't overwrite each other
    quant_data: Annotated[Dict[str, Any], merge_dicts]
    sentiment_data: Annotated[Dict[str, Any], merge_dicts]
    # THE FIX: Track the active token across the swarm nodes
    current_ticker: str 
    asset_class: str
    
    proposed_trade: Dict[str, Any]
    risk_approved: bool
    paper_trading_enabled: bool
