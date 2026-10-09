"""Transaction model."""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    TRANSFER = "TRANSFER"
    HOLD_CAPTURE = "HOLD_CAPTURE"
    HOLD_RELEASE = "HOLD_RELEASE"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    from_wallet_id: Mapped[int | None] = mapped_column(ForeignKey("wallets.id"), nullable=True, index=True)
    to_wallet_id: Mapped[int | None] = mapped_column(ForeignKey("wallets.id"), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, length=20, create_constraint=False),
        nullable=False,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, native_enum=False, length=20, create_constraint=False),
        nullable=False,
        default=TransactionStatus.COMPLETED,
        server_default=TransactionStatus.COMPLETED.value,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    from_wallet = relationship("Wallet", foreign_keys=[from_wallet_id], lazy="joined")
    to_wallet = relationship("Wallet", foreign_keys=[to_wallet_id], lazy="joined")
    ledger_entries = relationship("LedgerEntry", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin")
