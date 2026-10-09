"""Transaction schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.ledger_entry import LedgerEntryType
from app.models.transaction import TransactionStatus, TransactionType


class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_name: str
    entry_type: LedgerEntryType
    amount: float
    created_at: datetime


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_id: str
    from_wallet_id: Optional[int] = None
    to_wallet_id: Optional[int] = None
    from_wallet_number: Optional[str] = None
    to_wallet_number: Optional[str] = None
    from_user_name: Optional[str] = None
    to_user_name: Optional[str] = None
    amount: float
    currency: str
    type: TransactionType
    status: TransactionStatus
    description: Optional[str] = None
    failure_reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    ledger_entries: List[LedgerEntryResponse] = []


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
