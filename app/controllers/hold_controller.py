"""HTTP-level handling for holds."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hold import Hold, HoldStatus
from app.models.user import User
from app.schemas.hold import HoldCreateRequest, HoldResponse
from app.services import hold_service


def _format_hold(h: Hold) -> HoldResponse:
    return HoldResponse(
        id=h.id,
        hold_reference=h.hold_reference,
        wallet_id=h.wallet_id,
        amount=float(h.amount),
        currency=h.currency,
        reason=h.reason,
        status=h.status,
        expires_at=h.expires_at,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )


async def create_hold(
    db: AsyncSession,
    current_user: User,
    payload: HoldCreateRequest,
) -> HoldResponse:
    hold = await hold_service.create_hold(
        db=db,
        user=current_user,
        amount=payload.amount,
        reason=payload.reason,
    )
    return _format_hold(hold)


async def list_holds(
    db: AsyncSession,
    current_user: User,
    status: HoldStatus | None = None,
) -> list[HoldResponse]:
    holds = await hold_service.get_user_holds(
        db=db,
        user_id=current_user.id,
        status_filter=status,
    )
    return [_format_hold(h) for h in holds]


async def capture_hold(
    db: AsyncSession,
    current_user: User,
    hold_id: int,
) -> HoldResponse:
    hold, _ = await hold_service.capture_hold(
        db=db,
        hold_id=hold_id,
        user=current_user,
    )
    return _format_hold(hold)


async def release_hold(
    db: AsyncSession,
    current_user: User,
    hold_id: int,
) -> HoldResponse:
    hold, _ = await hold_service.release_hold(
        db=db,
        hold_id=hold_id,
        user=current_user,
    )
    return _format_hold(hold)
