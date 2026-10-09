"""Hold schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.hold import HoldStatus


class HoldCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2, description="Hold amount to reserve")
    reason: str = Field(min_length=2, max_length=255, description="Reason for hold (e.g. Escrow, Merchant Pre-Auth)")


class HoldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hold_reference: str
    wallet_id: int
    amount: float
    currency: str
    reason: str
    status: HoldStatus
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
