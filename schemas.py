from pydantic import BaseModel, Field
from typing import Optional

class TradeRequest(BaseModel):
    directive: str = Field(..., description="The user's trading command, e.g., 'TSLA market order 10 shares'")
    paper_trading: bool = Field(default=True, description="Safety flag to prevent real financial ruin")

class TradeResponse(BaseModel):
    status: str
    ticker: Optional[str] = None
    action: Optional[str] = None
    shares: Optional[int] = 0
    risk_approved: bool = False
    orchestrator_reasoning: Optional[str] = None
