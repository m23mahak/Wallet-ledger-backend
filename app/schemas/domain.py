from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.domain import TransactionStatus

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str

    class Config:
        orm_mode = True

class WalletCreate(BaseModel):
    currency: str = "USD"

class WalletResponse(BaseModel):
    id: str
    user_id: str
    currency: str
    balance: float

    class Config:
        orm_mode = True

class TransactionCreate(BaseModel):
    to_wallet_id: Optional[str]
    amount: float

class TransactionResponse(BaseModel):
    id: str
    from_wallet_id: Optional[str]
    to_wallet_id: Optional[str]
    amount: float
    status: TransactionStatus
    created_at: datetime

    class Config:
        orm_mode = True

class HoldCreate(BaseModel):
    amount: float
    reason: str

class HoldResponse(BaseModel):
    id: str
    wallet_id: str
    amount: float
    reason: str
    active: bool

    class Config:
        orm_mode = True
