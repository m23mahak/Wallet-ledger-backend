"""HTTP-level handling for transfers."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.transfer import TransferRequest, TransferResponse
from app.services import transfer_service


async def transfer(
    db: AsyncSession,
    current_user: User,
    payload: TransferRequest,
    idempotency_key: str | None = None,
    ip_address: str | None = None,
) -> TransferResponse:
    tx, sender_wallet, _ = await transfer_service.process_transfer(
        db=db,
        sender_user=current_user,
        recipient_identifier=payload.recipient,
        amount=payload.amount,
        description=payload.description,
        idempotency_key=idempotency_key,
        ip_address=ip_address,
    )

    to_wallet_num = tx.to_wallet.wallet_number if tx.to_wallet else "EXTERNAL"
    from_wallet_num = sender_wallet.wallet_number

    return TransferResponse(
        transaction_id=tx.id,
        reference_id=tx.reference_id,
        from_wallet_number=from_wallet_num,
        to_wallet_number=to_wallet_num,
        amount=float(tx.amount),
        currency=tx.currency,
        status=tx.status.value,
        description=tx.description,
        created_at=tx.created_at,
    )
