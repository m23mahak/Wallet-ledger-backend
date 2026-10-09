"""Wallet model."""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class WalletStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'FROZEN')", name="wallet_status_valid"),
        CheckConstraint("balance >= 0", name="wallet_balance_non_negative"),
        CheckConstraint("held_balance >= 0", name="wallet_held_balance_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    held_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    status: Mapped[WalletStatus] = mapped_column(
        Enum(WalletStatus, native_enum=False, length=20, create_constraint=False),
        nullable=False,
        default=WalletStatus.ACTIVE,
        server_default=WalletStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", backref="wallets", lazy="joined")

    @property
    def available_balance(self) -> Decimal:
        avail = self.balance - self.held_balance
        return avail if avail >= Decimal("0.00") else Decimal("0.00")
