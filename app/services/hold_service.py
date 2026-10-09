"""Hold service for reserving, capturing, and releasing funds."""
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    Forbidden,
    HoldNotFound,
    InsufficientBalance,
    InvalidHoldState,
    WalletFrozen,
    WalletNotFound,
)
from app.models.hold import Hold, HoldStatus
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User, UserRole
from app.models.wallet import Wallet, WalletStatus
from app.services import audit_service, wallet_service


async def create_hold(
    db: AsyncSession,
    user: User,
    amount: Decimal,
    reason: str,
) -> Hold:
    wallet = await wallet_service.get_wallet_by_user_id(db, user.id)
    if not wallet:
        raise WalletNotFound()

    if wallet.status != WalletStatus.ACTIVE:
        raise WalletFrozen("Cannot place a hold on a frozen wallet")

    if amount <= Decimal("0.00"):
        raise InsufficientBalance("Hold amount must be greater than zero")

    if wallet.available_balance < amount:
        raise InsufficientBalance(
            f"Insufficient available balance (₹{wallet.available_balance:,.2f}) to reserve ₹{amount:,.2f}"
        )

    # Reserve the amount by incrementing held_balance
    wallet.held_balance += amount

    ref = f"HLD-{uuid4().hex[:10].upper()}"
    hold = Hold(
        hold_reference=ref,
        wallet_id=wallet.id,
        amount=amount,
        currency=wallet.currency,
        reason=reason.strip(),
        status=HoldStatus.ACTIVE,
    )
    db.add(hold)
    await db.flush()

    await audit_service.record_audit(
        db=db,
        action="HOLD_CREATE",
        entity_type="HOLD",
        entity_id=str(hold.id),
        actor_id=user.id,
        actor_email=user.email,
        details={"hold_reference": ref, "amount": float(amount), "reason": reason},
    )

    await db.commit()
    await db.refresh(hold)
    return hold


async def get_user_holds(
    db: AsyncSession,
    user_id: int,
    status_filter: HoldStatus | None = None,
) -> list[Hold]:
    wallet = await wallet_service.get_wallet_by_user_id(db, user_id)
    if not wallet:
        return []

    stmt = select(Hold).where(Hold.wallet_id == wallet.id)
    if status_filter:
        stmt = stmt.where(Hold.status == status_filter)
    stmt = stmt.order_by(Hold.created_at.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_hold_by_id(db: AsyncSession, hold_id: int) -> Hold | None:
    return await db.get(Hold, hold_id)


async def capture_hold(
    db: AsyncSession,
    hold_id: int,
    user: User,
) -> tuple[Hold, Transaction]:
    hold = await db.get(Hold, hold_id)
    if not hold:
        raise HoldNotFound()

    wallet = await db.get(Wallet, hold.wallet_id)
    if not wallet:
        raise WalletNotFound()

    if user.role != UserRole.ADMIN and wallet.user_id != user.id:
        raise Forbidden("You do not have permission to capture this hold")

    if hold.status != HoldStatus.ACTIVE:
        raise InvalidHoldState(f"Hold is in {hold.status.value} state and cannot be captured")

    # Settle funds: deduct from held balance AND total balance
    wallet.held_balance -= hold.amount
    wallet.balance -= hold.amount
    hold.status = HoldStatus.CAPTURED

    ref_id = f"TXN-CAP-{uuid4().hex[:12].upper()}"
    tx = Transaction(
        reference_id=ref_id,
        from_wallet_id=wallet.id,
        to_wallet_id=None,
        amount=hold.amount,
        currency=wallet.currency,
        type=TransactionType.HOLD_CAPTURE,
        status=TransactionStatus.COMPLETED,
        description=f"Capture of Hold {hold.hold_reference} ({hold.reason})",
    )
    db.add(tx)
    await db.flush()

    # Double-entry ledger
    le_debit = LedgerEntry(
        transaction_id=tx.id,
        wallet_id=wallet.id,
        account_name=f"WALLET_{wallet.id}",
        entry_type=LedgerEntryType.DEBIT,
        amount=hold.amount,
    )
    le_credit = LedgerEntry(
        transaction_id=tx.id,
        wallet_id=None,
        account_name="SYSTEM_HOLD_ESCROW_SETTLED",
        entry_type=LedgerEntryType.CREDIT,
        amount=hold.amount,
    )
    db.add_all([le_debit, le_credit])

    await audit_service.record_audit(
        db=db,
        action="HOLD_CAPTURE",
        entity_type="HOLD",
        entity_id=str(hold.id),
        actor_id=user.id,
        actor_email=user.email,
        details={"hold_reference": hold.hold_reference, "transaction_id": tx.id},
    )

    await db.commit()
    await db.refresh(hold)
    await db.refresh(tx)
    return hold, tx


async def release_hold(
    db: AsyncSession,
    hold_id: int,
    user: User,
) -> tuple[Hold, Transaction]:
    hold = await db.get(Hold, hold_id)
    if not hold:
        raise HoldNotFound()

    wallet = await db.get(Wallet, hold.wallet_id)
    if not wallet:
        raise WalletNotFound()

    if user.role != UserRole.ADMIN and wallet.user_id != user.id:
        raise Forbidden("You do not have permission to release this hold")

    if hold.status != HoldStatus.ACTIVE:
        raise InvalidHoldState(f"Hold is in {hold.status.value} state and cannot be released")

    # Release funds: deduct from held balance (total balance stays unchanged)
    wallet.held_balance -= hold.amount
    hold.status = HoldStatus.RELEASED

    ref_id = f"TXN-REL-{uuid4().hex[:12].upper()}"
    tx = Transaction(
        reference_id=ref_id,
        from_wallet_id=wallet.id,
        to_wallet_id=None,
        amount=hold.amount,
        currency=wallet.currency,
        type=TransactionType.HOLD_RELEASE,
        status=TransactionStatus.COMPLETED,
        description=f"Release of Hold {hold.hold_reference} ({hold.reason})",
    )
    db.add(tx)
    await db.flush()

    await audit_service.record_audit(
        db=db,
        action="HOLD_RELEASE",
        entity_type="HOLD",
        entity_id=str(hold.id),
        actor_id=user.id,
        actor_email=user.email,
        details={"hold_reference": hold.hold_reference, "transaction_id": tx.id},
    )

    await db.commit()
    await db.refresh(hold)
    await db.refresh(tx)
    return hold, tx
