"""HTTP-level handling for wallet operations."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, WalletNotFound
from app.models.user import User, UserRole
from app.models.wallet import Wallet
from app.schemas.wallet import DepositRequest, WalletResponse
from app.services import wallet_service


def _format_wallet(w: Wallet) -> WalletResponse:
    return WalletResponse(
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


async def get_my_wallet(db: AsyncSession, current_user: User) -> WalletResponse:
    wallet = await wallet_service.get_or_create_wallet_for_user(db, current_user)
    return _format_wallet(wallet)


async def get_wallet_by_id(db: AsyncSession, current_user: User, wallet_id: int) -> WalletResponse:
    wallet = await wallet_service.get_wallet_by_id(db, wallet_id)
    if not wallet:
        raise WalletNotFound()
    if current_user.role != UserRole.ADMIN and wallet.user_id != current_user.id:
        raise Forbidden("You do not have access to this wallet")
    return _format_wallet(wallet)


async def deposit(
    db: AsyncSession,
    current_user: User,
    payload: DepositRequest,
) -> WalletResponse:
    wallet = await wallet_service.get_or_create_wallet_for_user(db, current_user)
    _, updated_wallet = await wallet_service.deposit_to_wallet(
        db=db,
        wallet_id=wallet.id,
        amount=payload.amount,
        description=payload.description,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    return _format_wallet(updated_wallet)
