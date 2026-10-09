"""Admin and operations schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole, UserStatus
from app.models.wallet import WalletStatus


class AdminDashboardResponse(BaseModel):
    total_users: int
    active_users: int
    blocked_users: int
    total_wallets: int
    active_wallets: int
    frozen_wallets: int
    total_transactions: int
    total_volume_inr: float
    success_rate_percent: float
    active_holds_count: int
    active_holds_amount_inr: float
    ledger_balanced: bool


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    status: UserStatus
    wallet_number: Optional[str] = None
    wallet_balance: Optional[float] = None
    created_at: datetime


class UserStatusUpdateRequest(BaseModel):
    status: UserStatus


class WalletStatusUpdateRequest(BaseModel):
    status: WalletStatus


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


class ReconciliationResponse(BaseModel):
    status: str  # "BALANCED" or "DISCREPANCY"
    total_debits: float
    total_credits: float
    net_system_balance: float
    checked_wallets: int
    discrepant_wallets: int
    details: List[str]
