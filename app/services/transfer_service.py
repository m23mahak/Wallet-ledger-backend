"""Transfer service implementing row locking, double-entry bookkeeping, idempotency, and risk checks."""
import json
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InsufficientBalance,
    InvalidRecipient,
    WalletNotFound,
)
from app.models.idempotency import IdempotencyRecord
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.models.wallet import Wallet
from app.services import audit_service, risk_service, wallet_service


async def process_transfer(
    db: AsyncSession,
    sender_user: User,
    recipient_identifier: str,
    amount: Decimal,
    description: str | None = None,
    idempotency_key: str | None = None,
    ip_address: str | None = None,
) -> tuple[Transaction, Wallet, bool]:
    """
    Executes a wallet-to-wallet transfer atomically.
    Returns (Transaction, SenderWallet, was_cached_idempotent).
    """
    # 1. Idempotency Check
    if idempotency_key:
        clean_key = idempotency_key.strip()
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.key == clean_key,
            IdempotencyRecord.user_id == sender_user.id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            cached_data = json.loads(existing.response_body)
            # Retrieve the transaction
            tx = await db.get(Transaction, cached_data["transaction_id"])
            sender_wallet = await wallet_service.get_wallet_by_user_id(db, sender_user.id)
            if tx and sender_wallet:
                return tx, sender_wallet, True

    # 2. Lookup sender wallet
    sender_wallet = await wallet_service.get_wallet_by_user_id(db, sender_user.id)
    if not sender_wallet:
        raise WalletNotFound("Sender wallet not found")

    # 3. Lookup recipient wallet
    recipient_wallet = await wallet_service.get_wallet_by_identifier(db, recipient_identifier)
    if not recipient_wallet:
        raise InvalidRecipient(f"Recipient '{recipient_identifier}' not found")

    # 4. Risk validation
    risk_service.validate_transfer_risk(sender_wallet, recipient_wallet, amount)

    # 5. Check available balance before lock
    if sender_wallet.available_balance < amount:
        raise InsufficientBalance(
            f"Available balance ₹{sender_wallet.available_balance:,.2f} is insufficient for transfer of ₹{amount:,.2f}"
        )

    # 6. Row-level locking in deterministic ID order to avoid deadlocks
    first_id, second_id = (
        (sender_wallet.id, recipient_wallet.id)
        if sender_wallet.id < recipient_wallet.id
        else (recipient_wallet.id, sender_wallet.id)
    )

    q1 = select(Wallet).where(Wallet.id == first_id)
    q2 = select(Wallet).where(Wallet.id == second_id)
    if db.bind and getattr(db.bind.dialect, "name", "") == "postgresql":
        q1 = q1.with_for_update()
        q2 = q2.with_for_update()

    w1 = (await db.execute(q1)).scalar_one()
    w2 = (await db.execute(q2)).scalar_one()

    locked_sender = w1 if w1.id == sender_wallet.id else w2
    locked_recipient = w2 if w2.id == recipient_wallet.id else w1

    # Re-verify balance on locked row
    if locked_sender.available_balance < amount:
        raise InsufficientBalance(
            f"Available balance ₹{locked_sender.available_balance:,.2f} is insufficient for transfer of ₹{amount:,.2f}"
        )

    # 7. Execute atomic balance updates
    locked_sender.balance -= amount
    locked_recipient.balance += amount

    # 8. Create Transaction
    ref_id = f"TXN-TRF-{uuid4().hex[:12].upper()}"
    desc = description.strip() if description else f"Transfer to {locked_recipient.wallet_number}"
    tx = Transaction(
        reference_id=ref_id,
        from_wallet_id=locked_sender.id,
        to_wallet_id=locked_recipient.id,
        amount=amount,
        currency=locked_sender.currency,
        type=TransactionType.TRANSFER,
        status=TransactionStatus.COMPLETED,
        description=desc,
        idempotency_key=idempotency_key.strip() if idempotency_key else None,
    )
    db.add(tx)
    await db.flush()

    # 9. Create Double-Entry Ledger Entries
    le_debit = LedgerEntry(
        transaction_id=tx.id,
        wallet_id=locked_sender.id,
        account_name=f"WALLET_{locked_sender.id}",
        entry_type=LedgerEntryType.DEBIT,
        amount=amount,
    )
    le_credit = LedgerEntry(
        transaction_id=tx.id,
        wallet_id=locked_recipient.id,
        account_name=f"WALLET_{locked_recipient.id}",
        entry_type=LedgerEntryType.CREDIT,
        amount=amount,
    )
    db.add_all([le_debit, le_credit])

    # 10. Audit logging
    await audit_service.record_audit(
        db=db,
        action="WALLET_TRANSFER",
        entity_type="TRANSACTION",
        entity_id=str(tx.id),
        actor_id=sender_user.id,
        actor_email=sender_user.email,
        details={
            "reference_id": ref_id,
            "from_wallet": locked_sender.wallet_number,
            "to_wallet": locked_recipient.wallet_number,
            "amount": float(amount),
        },
        ip_address=ip_address,
    )

    # 11. Store Idempotency Record if key provided
    if idempotency_key:
        idempotent_resp = {
            "transaction_id": tx.id,
            "reference_id": tx.reference_id,
            "amount": float(amount),
            "status": tx.status.value,
        }
        db.add(
            IdempotencyRecord(
                key=idempotency_key.strip(),
                user_id=sender_user.id,
                endpoint="/api/v1/transfers",
                response_status_code=200,
                response_body=json.dumps(idempotent_resp),
            )
        )

    await db.commit()
    await db.refresh(locked_sender)
    await db.refresh(tx)
    return tx, locked_sender, False
