"""Transfer schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransferRequest(BaseModel):
    recipient: str = Field(min_length=1, max_length=255, description="Recipient Wallet Number (e.g. WLT-0001) or email")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Transfer amount in INR (must be positive)")
    description: Optional[str] = Field(default=None, max_length=255)


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: int
    reference_id: str
    from_wallet_number: str
    to_wallet_number: str
    amount: float
    currency: str
    status: str
    description: Optional[str] = None
    created_at: datetime
