from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal


class TradeRequest(BaseModel):
    directive: str = Field(..., description="The user's trading command")
    paper_trading: bool = Field(
        default=True, description="Safety flag to prevent real money loss"
    )


class TradeResponse(BaseModel):
    status: str = Field(..., description="Success or error status")
    ticker: Optional[str] = None
    action: Optional[Literal["BUY", "SELL", "HOLD", "REJECT"]] = None
    shares: Optional[float] = None
    risk_approved: bool = False
    orchestrator_reasoning: Optional[str] = None
    error_message: Optional[str] = None


class TradeDirectiveSchema(BaseModel):
    model_config = ConfigDict(strict=False, extra="forbid")

    is_valid_directive: bool = Field(
        description="Set to True ONLY if the user provides a specific ticker."
    )
    ticker: Optional[str] = Field(
        default=None, description="The financial asset ticker symbol."
    )
    asset_class: Literal["crypto", "equity", "unknown"] = Field(default="equity")
    rejection_reason: Optional[str] = Field(default=None)
    action: Literal["BUY", "SELL", "HOLD", "REJECT"] = Field(default="HOLD")
    quantity: Optional[float] = Field(default=None)
    allocation: Optional[float] = Field(
        default=None,
        description="Portfolio allocation fraction (0.0 to 1.0).",
    )
    risk_threshold: Optional[float] = Field(default=0.5)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker_format(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        clean_value = value.upper().strip()

        # Preserve Indian market exchange suffixes (.NS for NSE, .BO for BSE)
        if clean_value.endswith(".NS") or clean_value.endswith(".BO"):
            return clean_value

        # Alpaca requires slash for crypto
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
