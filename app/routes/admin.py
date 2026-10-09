"""Admin operations endpoints."""
from typing import Optional
from fastapi import APIRouter, Query, status

from app.controllers import admin_controller
from app.core.dependencies import CurrentAdmin, DbSession
from app.models.transaction import TransactionStatus, TransactionType
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminUserResponse,
    AuditLogResponse,
    ReconciliationResponse,
    UserStatusUpdateRequest,
    WalletStatusUpdateRequest,
)
from app.schemas.common import SuccessResponse
from app.schemas.transaction import TransactionListResponse
from app.schemas.wallet import WalletResponse
from app.services import ledger_service
from app.routes.transactions import _format_transaction

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/dashboard",
    response_model=SuccessResponse[AdminDashboardResponse],
    summary="Admin dashboard system overview and metrics",
)
async def get_dashboard(admin: CurrentAdmin, db: DbSession):
    return SuccessResponse(data=await admin_controller.get_dashboard_stats(db))


@router.get(
    "/users",
    response_model=SuccessResponse[list[AdminUserResponse]],
    summary="List all users with roles and wallet details",
)
async def list_users(admin: CurrentAdmin, db: DbSession):
    return SuccessResponse(data=await admin_controller.get_all_users(db))


@router.patch(
    "/users/{user_id}/status",
    response_model=SuccessResponse[AdminUserResponse],
    summary="Block or unblock a user account",
)
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    admin: CurrentAdmin,
    db: DbSession,
):
    return SuccessResponse(
        data=await admin_controller.update_user_status(
            db=db,
            current_admin=admin,
            target_user_id=user_id,
            new_status=payload.status,
        )
    )


@router.get(
    "/wallets",
    response_model=SuccessResponse[list[WalletResponse]],
    summary="List all system wallets",
)
async def list_wallets(admin: CurrentAdmin, db: DbSession):
    return SuccessResponse(data=await admin_controller.get_all_wallets(db))


@router.patch(
    "/wallets/{wallet_id}/status",
    response_model=SuccessResponse[WalletResponse],
    summary="Freeze or unfreeze a wallet",
)
async def update_wallet_status(
    wallet_id: int,
    payload: WalletStatusUpdateRequest,
    admin: CurrentAdmin,
    db: DbSession,
):
    return SuccessResponse(
        data=await admin_controller.update_wallet_status(
            db=db,
            current_admin=admin,
            wallet_id=wallet_id,
            new_status=payload.status,
        )
    )


@router.get(
    "/transactions",
    response_model=SuccessResponse[TransactionListResponse],
    summary="Query all system transactions with filters",
)
async def list_all_transactions(
    admin: CurrentAdmin,
    db: DbSession,
    type: Optional[TransactionType] = Query(None),
    status: Optional[TransactionStatus] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await ledger_service.get_transactions(
        db=db,
        wallet_id=None,  # system-wide
        tx_type=type,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return SuccessResponse(
        data=TransactionListResponse(
            items=[_format_transaction(tx) for tx in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get(
    "/audit-logs",
    response_model=SuccessResponse[list[AuditLogResponse]],
    summary="View immutable system audit logs",
)
async def list_audit_logs(
    admin: CurrentAdmin,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
):
    return SuccessResponse(data=await admin_controller.get_audit_logs(db, limit=limit))


@router.get(
    "/reconciliation",
    response_model=SuccessResponse[ReconciliationResponse],
    summary="Run live ledger and wallet balance reconciliation",
)
async def run_reconciliation(admin: CurrentAdmin, db: DbSession):
    return SuccessResponse(data=await admin_controller.get_reconciliation_report(db))
