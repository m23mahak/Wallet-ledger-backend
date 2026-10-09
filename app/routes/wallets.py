"""Wallet endpoints."""
from fastapi import APIRouter, status

from app.controllers import wallet_controller
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.wallet import DepositRequest, WalletResponse

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.get(
    "/me",
    response_model=SuccessResponse[WalletResponse],
    summary="Get current user wallet",
    description="Returns the authenticated user's wallet with balance and hold metrics.",
)
async def get_my_wallet(user: CurrentUser, db: DbSession):
    return SuccessResponse(data=await wallet_controller.get_my_wallet(db, user))


@router.post(
    "/deposit",
    response_model=SuccessResponse[WalletResponse],
    status_code=status.HTTP_200_OK,
    summary="Deposit funds into current user wallet",
    description="Simulated fund top-up with double-entry ledger bookkeeping.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid deposit amount"},
        403: {"model": ErrorResponse, "description": "Wallet is frozen"},
    },
)
async def deposit_funds(payload: DepositRequest, user: CurrentUser, db: DbSession):
    return SuccessResponse(data=await wallet_controller.deposit(db, user, payload))


@router.get(
    "/{wallet_id}",
    response_model=SuccessResponse[WalletResponse],
    summary="Get wallet by ID",
    responses={
        403: {"model": ErrorResponse, "description": "Access forbidden"},
        404: {"model": ErrorResponse, "description": "Wallet not found"},
    },
)
async def get_wallet(wallet_id: int, user: CurrentUser, db: DbSession):
    return SuccessResponse(data=await wallet_controller.get_wallet_by_id(db, user, wallet_id))
