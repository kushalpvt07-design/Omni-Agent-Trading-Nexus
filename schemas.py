from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

class TradeRequest(BaseModel):
    directive: str = Field(..., description="The user's trading command")
    paper_trading: bool = Field(default=True, description="Safety flag")

class TradeResponse(BaseModel):
    status: str
    ticker: Optional[str] = None
    action: Optional[str] = None
    shares: Optional[float] = 0.0
    risk_approved: bool = False
    orchestrator_reasoning: Optional[str] = None
    error_message: Optional[str] = None

class TradeDirectiveSchema(BaseModel):
    is_valid_directive: bool = Field(description="Set to True ONLY if the user provides a specific ticker.")
    ticker: Optional[str] = Field(default=None, description="The financial asset ticker symbol.")
    asset_class: Literal["crypto", "equity", "unknown"] = Field(default="equity")
    rejection_reason: Optional[str] = Field(default=None)
    action: Literal["BUY", "SELL", "HOLD"] = Field(default="HOLD")
    quantity: Optional[float] = Field(default=None)
    allocation_percentage: Optional[float] = Field(default=None)
    risk_threshold: Optional[float] = Field(default=0.5)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker_format(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        clean_value = value.upper().strip()
        
        # FACT: Alpaca requires the slash for crypto. DO NOT USE DASHES HERE.
        if "-" in clean_value:
            clean_value = clean_value.replace("-", "/")
            
        crypto_bases = {"BTC", "ETH", "SOL", "DOGE", "ADA", "XRP"}
        if clean_value in crypto_bases:
            clean_value = f"{clean_value}/USD"
            
        return clean_value

    @field_validator("asset_class", mode="before")
    @classmethod
    def normalize_asset_class(cls, value: Optional[str]) -> str:
        if not value:
            return "equity"
        clean_val = value.lower().strip()
        return clean_val if clean_val in ["crypto", "equity"] else "unknown"
