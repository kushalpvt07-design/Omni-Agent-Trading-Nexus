from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from langchain_core.messages import BaseMessage

# Reducer function to safely merge dictionaries instead of overwriting them
def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {**(a or {}), **(b or {})}

# Define the exact structure of a trade proposal so the execution node doesn't guess
class TradeProposal(TypedDict, total=False):
    action: str          # BUY, SELL, HOLD
    ticker: str
    quantity: Optional[float]
    allocation: Optional[float]
    reasoning: str

class FinancialSwarmState(TypedDict):
    # Core Communication
    messages: Annotated[List[BaseMessage], operator.add]
    errors: Annotated[List[str], operator.add]
    
    # Swarm Data Context
    quant_data: Annotated[Dict[str, Any], merge_dicts]
    sentiment_data: Annotated[Dict[str, Any], merge_dicts]
    
    # Extracted Entities (Optional because parser might fail or not find them yet)
    current_ticker: Optional[str] 
    asset_class: Optional[str]
    
    # User's exact request extracted by parser (Strictly Typed)
    requested_action: Optional[str]
    requested_quantity: Optional[float]
    requested_allocation: Optional[float]
    risk_threshold: Optional[float]
    
    # Execution & Rules
    proposed_trade: TradeProposal
    risk_approved: bool
    paper_trading_enabled: bool
