from pydantic import BaseModel, Field
from typing import Optional

class TradeRequest(BaseModel):
    directive: str = Field(..., description="The user's trading command, e.g., 'TSLA market order 10 shares'")
    paper_trading: bool = Field(default=True, description="Safety flag to prevent real financial ruin")

class TradeResponse(BaseModel):
    status: str
    ticker: Optional[str] = None
    action: Optional[str] = None
    shares: Optional[float] = 0.0
    risk_approved: bool = False
    orchestrator_reasoning: Optional[str] = None
    error_message: Optional[str] = None

class TradeDirectiveSchema(BaseModel):
    is_valid_directive: bool = Field(description="Set to True ONLY if the user provides a specific, unambiguous ticker or company to analyze.")
    ticker: Optional[str] = Field(default=None, description="The stock ticker symbol (e.g., NVDA, AAPL).")
    asset_class: Optional[str] = Field(default=None, description="Must be 'crypto' or 'equity'")
    rejection_reason: Optional[str] = Field(default=None, description="If is_valid_directive is False, explain why.")
    action: Optional[str] = Field(default="BUY", description="Must be BUY, SELL, or HOLD.")
    quantity: Optional[float] = Field(default=None, description="Exact number of shares requested (e.g., 10 shares). DO NOT confuse this with percentage.")
    allocation_percentage: Optional[float] = Field(default=None, description="Percentage of portfolio to allocate (e.g., 10%).")
    risk_threshold: Optional[float] = Field(default=0.5, description="Maximum acceptable risk threshold mentioned by user. Defaults to 0.5 (50%)")
