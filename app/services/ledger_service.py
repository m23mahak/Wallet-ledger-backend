"""Ledger service for querying transactions, statements, and double-entry details."""
from datetime import datetime
from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import TransactionNotFound
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.wallet import Wallet


async def get_transactions(
    db: AsyncSession,
    wallet_id: int | None = None,
    tx_type: TransactionType | None = None,
    status: TransactionStatus | None = None,
    search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Transaction], int]:
    stmt = select(Transaction).options(
        selectinload(Transaction.from_wallet).selectinload(Wallet.user),
        selectinload(Transaction.to_wallet).selectinload(Wallet.user),
        selectinload(Transaction.ledger_entries),
    )

    if wallet_id is not None:
        stmt = stmt.where(
            or_(
                Transaction.from_wallet_id == wallet_id,
                Transaction.to_wallet_id == wallet_id,
            )
        )

    if tx_type is not None:
        stmt = stmt.where(Transaction.type == tx_type)

    if status is not None:
        stmt = stmt.where(Transaction.status == status)

    if start_date is not None:
        stmt = stmt.where(Transaction.created_at >= start_date)

    if end_date is not None:
        stmt = stmt.where(Transaction.created_at <= end_date)

    if search:
        s = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Transaction.reference_id.ilike(s),
                Transaction.description.ilike(s),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order by newest first
    stmt = stmt.order_by(Transaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())

    return items, total


async def get_transaction_by_id(db: AsyncSession, tx_id: int) -> Transaction:
    stmt = (
        select(Transaction)
        .options(
            selectinload(Transaction.from_wallet).selectinload(Wallet.user),
            selectinload(Transaction.to_wallet).selectinload(Wallet.user),
            selectinload(Transaction.ledger_entries),
        )
        .where(Transaction.id == tx_id)
    )
    tx = (await db.execute(stmt)).scalar_one_or_none()
    if not tx:
        raise TransactionNotFound()
    return tx
