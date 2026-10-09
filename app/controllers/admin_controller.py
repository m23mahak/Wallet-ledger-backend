"""HTTP-level handling for admin and operations endpoints."""
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import UserBlocked, WalletNotFound
from app.models.audit_log import AuditLog
from app.models.hold import Hold, HoldStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserStatus
from app.models.wallet import Wallet, WalletStatus
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminUserResponse,
    AuditLogResponse,
    ReconciliationResponse,
)
from app.schemas.wallet import WalletResponse
from app.services import audit_service, reconciliation_service


async def get_dashboard_stats(db: AsyncSession) -> AdminDashboardResponse:
    # Users count
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.status == UserStatus.ACTIVE))
    ).scalar() or 0
    blocked_users = (
        await db.execute(select(func.count(User.id)).where(User.status == UserStatus.BLOCKED))
    ).scalar() or 0

    # Wallets count
    total_wallets = (await db.execute(select(func.count(Wallet.id)))).scalar() or 0
    active_wallets = (
        await db.execute(select(func.count(Wallet.id)).where(Wallet.status == WalletStatus.ACTIVE))
    ).scalar() or 0
    frozen_wallets = (
        await db.execute(select(func.count(Wallet.id)).where(Wallet.status == WalletStatus.FROZEN))
    ).scalar() or 0

    # Transactions & Volume
    total_tx = (await db.execute(select(func.count(Transaction.id)))).scalar() or 0
    completed_tx = (
        await db.execute(select(func.count(Transaction.id)).where(Transaction.status == TransactionStatus.COMPLETED))
    ).scalar() or 0
    total_vol = (
        await db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.status == TransactionStatus.COMPLETED))
    ).scalar() or 0

    success_rate = (completed_tx / total_tx * 100.0) if total_tx > 0 else 100.0

    # Holds
    active_holds_count = (
        await db.execute(select(func.count(Hold.id)).where(Hold.status == HoldStatus.ACTIVE))
    ).scalar() or 0
    active_holds_amt = (
        await db.execute(select(func.coalesce(func.sum(Hold.amount), 0)).where(Hold.status == HoldStatus.ACTIVE))
    ).scalar() or 0

    # Quick ledger check
    rec = await reconciliation_service.run_reconciliation(db)
    is_balanced = rec["status"] == "BALANCED"

    return AdminDashboardResponse(
        total_users=total_users,
        active_users=active_users,
        blocked_users=blocked_users,
        total_wallets=total_wallets,
        active_wallets=active_wallets,
        frozen_wallets=frozen_wallets,
        total_transactions=total_tx,
        total_volume_inr=float(total_vol),
        success_rate_percent=round(success_rate, 2),
        active_holds_count=active_holds_count,
        active_holds_amount_inr=float(active_holds_amt),
        ledger_balanced=is_balanced,
    )


async def get_all_users(db: AsyncSession) -> list[AdminUserResponse]:
    stmt = select(User).options(selectinload(User.wallets)).order_by(User.id.asc())
    users = list((await db.execute(stmt)).scalars().all())

    items = []
    for u in users:
        primary_wallet = u.wallets[0] if u.wallets else None
        items.append(
            AdminUserResponse(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role,
                status=u.status,
                wallet_number=primary_wallet.wallet_number if primary_wallet else None,
                wallet_balance=float(primary_wallet.balance) if primary_wallet else 0.0,
                created_at=u.created_at,
            )
        )
    return items


async def update_user_status(
    db: AsyncSession,
    current_admin: User,
    target_user_id: int,
    new_status: UserStatus,
) -> AdminUserResponse:
    target = await db.get(User, target_user_id)
    if not target:
        raise UserBlocked("Target user not found")

    target.status = new_status
    await audit_service.record_audit(
        db=db,
        action="USER_STATUS_UPDATE",
        entity_type="USER",
        entity_id=str(target.id),
        actor_id=current_admin.id,
        actor_email=current_admin.email,
        details={"new_status": new_status.value},
    )
    await db.commit()
    await db.refresh(target)

    primary_wallet = target.wallets[0] if target.wallets else None
    return AdminUserResponse(
        id=target.id,
        name=target.name,
        email=target.email,
        role=target.role,
        status=target.status,
        wallet_number=primary_wallet.wallet_number if primary_wallet else None,
        wallet_balance=float(primary_wallet.balance) if primary_wallet else 0.0,
        created_at=target.created_at,
    )


async def get_all_wallets(db: AsyncSession) -> list[WalletResponse]:
    stmt = select(Wallet).order_by(Wallet.id.asc())
    wallets = list((await db.execute(stmt)).scalars().all())
    return [
        WalletResponse(
            id=w.id,
            wallet_number=w.wallet_number,
            user_id=w.user_id,
            currency=w.currency,
            balance=float(w.balance),
            held_balance=float(w.held_balance),
            available_balance=float(w.available_balance),
            status=w.status,
            created_at=w.created_at,
        )
        for w in wallets
    ]


async def update_wallet_status(
    db: AsyncSession,
    current_admin: User,
    wallet_id: int,
    new_status: WalletStatus,
) -> WalletResponse:
    wallet = await db.get(Wallet, wallet_id)
    if not wallet:
        raise WalletNotFound()

    wallet.status = new_status
    await audit_service.record_audit(
        db=db,
        action="WALLET_STATUS_UPDATE",
        entity_type="WALLET",
        entity_id=str(wallet.id),
        actor_id=current_admin.id,
        actor_email=current_admin.email,
        details={"new_status": new_status.value},
    )
    await db.commit()
    await db.refresh(wallet)

    return WalletResponse(
        id=wallet.id,
        wallet_number=wallet.wallet_number,
        user_id=wallet.user_id,
        currency=wallet.currency,
        balance=float(wallet.balance),
        held_balance=float(wallet.held_balance),
        available_balance=float(wallet.available_balance),
        status=wallet.status,
        created_at=wallet.created_at,
    )


async def get_audit_logs(
    db: AsyncSession,
    limit: int = 50,
) -> list[AuditLogResponse]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    logs = list((await db.execute(stmt)).scalars().all())
    return [AuditLogResponse.model_validate(log) for log in logs]


async def get_reconciliation_report(db: AsyncSession) -> ReconciliationResponse:
    res = await reconciliation_service.run_reconciliation(db)
    return ReconciliationResponse(**res)
