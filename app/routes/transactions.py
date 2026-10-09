"""Transaction query and statement endpoints."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import Forbidden
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import UserRole
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.transaction import (
    LedgerEntryResponse,
    TransactionListResponse,
    TransactionResponse,
)
from app.services import ledger_service, wallet_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _format_transaction(tx: Transaction) -> TransactionResponse:
    from_wallet_num = tx.from_wallet.wallet_number if tx.from_wallet else None
    to_wallet_num = tx.to_wallet.wallet_number if tx.to_wallet else None
    from_name = tx.from_wallet.user.name if (tx.from_wallet and tx.from_wallet.user) else None
    to_name = tx.to_wallet.user.name if (tx.to_wallet and tx.to_wallet.user) else None

    le_responses = [
        LedgerEntryResponse(
            id=le.id,
            account_name=le.account_name,
            entry_type=le.entry_type,
            amount=float(le.amount),
            created_at=le.created_at,
        )
        for le in tx.ledger_entries
    ]

    return TransactionResponse(
        id=tx.id,
        reference_id=tx.reference_id,
        from_wallet_id=tx.from_wallet_id,
        to_wallet_id=tx.to_wallet_id,
        from_wallet_number=from_wallet_num,
        to_wallet_number=to_wallet_num,
        from_user_name=from_name,
        to_user_name=to_name,
        amount=float(tx.amount),
        currency=tx.currency,
        type=tx.type,
        status=tx.status,
        description=tx.description,
        failure_reason=tx.failure_reason,
        idempotency_key=tx.idempotency_key,
        created_at=tx.created_at,
        ledger_entries=le_responses,
    )


@router.get(
    "",
    response_model=SuccessResponse[TransactionListResponse],
    summary="List transactions for the authenticated user",
    description="Returns filtered and paginated transactions with details.",
)
async def list_transactions(
    user: CurrentUser,
    db: DbSession,
    type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    status: Optional[TransactionStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search reference ID or description"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    wallet = await wallet_service.get_wallet_by_user_id(db, user.id)
    wallet_id = wallet.id if wallet else -1

    items, total = await ledger_service.get_transactions(
        db=db,
        wallet_id=wallet_id,
        tx_type=type,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    data = TransactionListResponse(
        items=[_format_transaction(tx) for tx in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return SuccessResponse(data=data)


@router.get(
    "/{transaction_id}",
    response_model=SuccessResponse[TransactionResponse],
    summary="Get single transaction detail with ledger entries",
    responses={
        403: {"model": ErrorResponse, "description": "Access forbidden"},
        404: {"model": ErrorResponse, "description": "Transaction not found"},
    },
)
async def get_transaction(transaction_id: int, user: CurrentUser, db: DbSession):
    tx = await ledger_service.get_transaction_by_id(db, transaction_id)
    wallet = await wallet_service.get_wallet_by_user_id(db, user.id)
    user_wallet_id = wallet.id if wallet else None

    # Normal users can only view transactions where their wallet was sender or receiver
    if (
        user.role != UserRole.ADMIN
        and tx.from_wallet_id != user_wallet_id
        and tx.to_wallet_id != user_wallet_id
    ):
        raise Forbidden("You do not have access to this transaction")

    return SuccessResponse(data=_format_transaction(tx))
