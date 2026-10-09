"""Wallet schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.wallet import WalletStatus


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_number: str
    user_id: int
    currency: str
    balance: float
    held_balance: float
    available_balance: float
    status: WalletStatus
    created_at: datetime


class DepositRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2, description="Deposit amount in INR (must be positive)")
    description: Optional[str] = Field(default="Account Deposit", max_length=255)
