"""Hold endpoints."""
from typing import Optional
from fastapi import APIRouter, Query, status

from app.controllers import hold_controller
from app.core.dependencies import CurrentUser, DbSession
from app.models.hold import HoldStatus
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.hold import HoldCreateRequest, HoldResponse

router = APIRouter(prefix="/holds", tags=["Holds"])


@router.post(
    "",
    response_model=SuccessResponse[HoldResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new fund hold",
    description="Reserves money from available balance for escrow or pre-authorization.",
    responses={
        400: {"model": ErrorResponse, "description": "Insufficient available balance"},
        403: {"model": ErrorResponse, "description": "Wallet is frozen"},
    },
)
async def create_hold(payload: HoldCreateRequest, user: CurrentUser, db: DbSession):
    return SuccessResponse(data=await hold_controller.create_hold(db, user, payload))


@router.get(
    "",
    response_model=SuccessResponse[list[HoldResponse]],
    summary="List holds for authenticated user",
)
async def list_holds(
    user: CurrentUser,
    db: DbSession,
    status: Optional[HoldStatus] = Query(None, description="Filter by status (ACTIVE, CAPTURED, RELEASED)"),
):
    return SuccessResponse(data=await hold_controller.list_holds(db, user, status=status))


@router.post(
    "/{hold_id}/capture",
    response_model=SuccessResponse[HoldResponse],
    summary="Capture an active hold",
    description="Finalizes transaction, settling held funds and moving money to escrow settlement.",
    responses={
        400: {"model": ErrorResponse, "description": "Hold is not active"},
        404: {"model": ErrorResponse, "description": "Hold not found"},
    },
)
async def capture_hold(hold_id: int, user: CurrentUser, db: DbSession):
    return SuccessResponse(data=await hold_controller.capture_hold(db, user, hold_id))


@router.post(
    "/{hold_id}/release",
    response_model=SuccessResponse[HoldResponse],
    summary="Release an active hold",
    description="Releases reserved funds back into the user's available balance.",
    responses={
        400: {"model": ErrorResponse, "description": "Hold is not active"},
        404: {"model": ErrorResponse, "description": "Hold not found"},
    },
)
async def release_hold(hold_id: int, user: CurrentUser, db: DbSession):
    return SuccessResponse(data=await hold_controller.release_hold(db, user, hold_id))
