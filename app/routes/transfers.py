"""Transfer endpoints."""
from typing import Optional
from fastapi import APIRouter, Header, Request, status

from app.controllers import transfer_controller
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.transfer import TransferRequest, TransferResponse

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post(
    "",
    response_model=SuccessResponse[TransferResponse],
    status_code=status.HTTP_200_OK,
    summary="Transfer money to another wallet",
    description="Atomic fund transfer with row-level locking, double-entry ledger bookkeeping, and idempotency.",
    responses={
        400: {"model": ErrorResponse, "description": "Insufficient balance or risk check failed"},
        403: {"model": ErrorResponse, "description": "Wallet frozen or account blocked"},
        404: {"model": ErrorResponse, "description": "Recipient not found"},
    },
)
async def create_transfer(
    payload: TransferRequest,
    user: CurrentUser,
    db: DbSession,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    ip_addr = request.client.host if request.client else None
    res = await transfer_controller.transfer(
        db=db,
        current_user=user,
        payload=payload,
        idempotency_key=idempotency_key,
        ip_address=ip_addr,
    )
    return SuccessResponse(data=res)
