import enum
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    currency = Column(String, default="USD")
    balance = Column(Float, default=0.0)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    from_wallet_id = Column(String, ForeignKey("wallets.id"), nullable=True)
    to_wallet_id = Column(String, ForeignKey("wallets.id"), nullable=True)
    amount = Column(Float)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    transaction_id = Column(String, ForeignKey("transactions.id"))
    wallet_id = Column(String, ForeignKey("wallets.id"))
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Hold(Base):
    __tablename__ = "holds"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    wallet_id = Column(String, ForeignKey("wallets.id"))
    amount = Column(Float)
    reason = Column(String)
    active = Column(Boolean, default=True)

class Idempotency(Base):
    __tablename__ = "idempotency_keys"
    key = Column(String, primary_key=True)
    response_data = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
