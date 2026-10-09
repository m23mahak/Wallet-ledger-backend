"""Wallet service for balance management and deposits."""
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WalletFrozen, WalletNotFound
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.models.wallet import Wallet, WalletStatus
from app.services import audit_service


async def get_wallet_by_user_id(db: AsyncSession, user_id: int) -> Wallet | None:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    return result.scalar_one_or_none()


async def get_or_create_wallet_for_user(db: AsyncSession, user: User, currency: str = "INR") -> Wallet:
    wallet = await get_wallet_by_user_id(db, user.id)
    if wallet is not None:
        return wallet

    wallet_number = f"WLT-{user.id:04d}"
    wallet = Wallet(
        wallet_number=wallet_number,
        user_id=user.id,
        currency=currency,
        balance=Decimal("0.00"),
        held_balance=Decimal("0.00"),
        status=WalletStatus.ACTIVE,
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)

    await audit_service.record_audit(
        db=db,
        action="WALLET_CREATE",
        entity_type="WALLET",
        entity_id=str(wallet.id),
        actor_id=user.id,
        actor_email=user.email,
        details={"wallet_number": wallet_number, "currency": currency},
    )
    await db.commit()
    return wallet


async def get_wallet_by_id(db: AsyncSession, wallet_id: int) -> Wallet | None:
    return await db.get(Wallet, wallet_id)


async def get_wallet_by_identifier(db: AsyncSession, identifier: str) -> Wallet | None:
    ident = identifier.strip()
    # 1. Try wallet number exact match
    res = await db.execute(select(Wallet).where(Wallet.wallet_number.ilike(ident)))
    wallet = res.scalar_one_or_none()
    if wallet:
        return wallet

    # 2. Try numeric ID
    if ident.isdigit():
        wallet = await db.get(Wallet, int(ident))
        if wallet:
            return wallet

    # 3. Try user email match
    user_res = await db.execute(select(User).where(User.email.ilike(ident)))
    user = user_res.scalar_one_or_none()
    if user:
        return await get_wallet_by_user_id(db, user.id)

    return None


async def deposit_to_wallet(
    db: AsyncSession,
    wallet_id: int,
    amount: Decimal,
    description: str | None,
    actor_id: int,
    actor_email: str,
) -> tuple[Transaction, Wallet]:
    wallet = await db.get(Wallet, wallet_id)
    if not wallet:
        raise WalletNotFound()

    if wallet.status != WalletStatus.ACTIVE:
        raise WalletFrozen("Cannot deposit into a frozen wallet")

    ref_id = f"TXN-DEP-{uuid4().hex[:12].upper()}"

    # Update wallet balance
    wallet.balance += amount

    # Create transaction
    tx = Transaction(
        reference_id=ref_id,
        from_wallet_id=None,
        to_wallet_id=wallet.id,
        amount=amount,
        currency=wallet.currency,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        description=description or "Demo Funds Top-up",
    )
    db.add(tx)
    await db.flush()

    # Create Double-Entry Ledger records
    # Debit system source, credit user wallet
    le_sys = LedgerEntry(
        transaction_id=tx.id,
        wallet_id=None,
        account_name="SYSTEM_DEPOSIT_SOURCE",
        entry_type=LedgerEntryType.DEBIT,
        amount=amount,
    )
    le_user = LedgerEntry(
        transaction_id=tx.id,
        wallet_id=wallet.id,
        account_name=f"WALLET_{wallet.id}",
        entry_type=LedgerEntryType.CREDIT,
        amount=amount,
    )
    db.add_all([le_sys, le_user])

    await audit_service.record_audit(
        db=db,
        action="WALLET_DEPOSIT",
        entity_type="WALLET",
        entity_id=str(wallet.id),
        actor_id=actor_id,
        actor_email=actor_email,
        details={"reference_id": ref_id, "amount": float(amount)},
    )

    await db.commit()
    await db.refresh(wallet)
    await db.refresh(tx)
    return tx, wallet
