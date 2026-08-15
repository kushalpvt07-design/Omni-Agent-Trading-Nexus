from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from langchain_core.messages import BaseMessage


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer function to safely merge dictionaries instead of overwriting them."""
    return {**(a or {}), **(b or {})}


class TradeProposal(TypedDict, total=False):
    """Exact structure of a trade proposal so the execution node doesn't guess."""
    action: str          # BUY, SELL, HOLD
    ticker: str
    shares: Optional[float]
    allocation: Optional[float]
    estimated_price: Optional[float]
    reasoning: str


class FinancialSwarmState(TypedDict):
    """Central state schema for the LangGraph trading swarm."""

    # Core Communication
    messages: Annotated[List[BaseMessage], operator.add]
    errors: Annotated[List[str], operator.add]

    # Swarm Data Context
    quant_data: Annotated[Dict[str, Any], merge_dicts]
    sentiment_data: Annotated[Dict[str, Any], merge_dicts]

    # Extracted Entities
    current_ticker: Optional[str]
    asset_class: Optional[str]

    # User's exact request extracted by parser
    requested_action: Optional[str]
    requested_quantity: Optional[float]
    requested_allocation: Optional[float]
    risk_threshold: Optional[float]

    # Execution & Rules
    proposed_trade: TradeProposal
    risk_approved: bool
    paper_trading_enabled: bool

    # Human-in-the-Loop safety checks
    requires_human_approval: bool
    human_approved: bool
