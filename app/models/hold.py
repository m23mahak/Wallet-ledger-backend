"""Hold model for reserving funds."""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class HoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CAPTURED = "CAPTURED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class Hold(Base):
    __tablename__ = "holds"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'CAPTURED', 'RELEASED', 'EXPIRED')", name="hold_status_valid"),
        CheckConstraint("amount > 0", name="hold_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hold_reference: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[HoldStatus] = mapped_column(
        Enum(HoldStatus, native_enum=False, length=20, create_constraint=False),
        nullable=False,
        default=HoldStatus.ACTIVE,
        server_default=HoldStatus.ACTIVE.value,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    wallet = relationship("Wallet", backref="holds", lazy="joined")
