"""Risk and compliance checks for financial movements."""
from decimal import Decimal

from app.core.exceptions import (
    RiskLimitExceeded,
    SelfTransferNotAllowed,
    WalletFrozen,
)
from app.models.wallet import Wallet, WalletStatus

MAX_SINGLE_TRANSFER_INR = Decimal("500000.00")  # 5 Lakh INR max per transfer


def validate_transfer_risk(
    sender_wallet: Wallet,
    recipient_wallet: Wallet,
    amount: Decimal,
) -> None:
    if amount <= Decimal("0.00"):
        raise RiskLimitExceeded("Transfer amount must be strictly greater than zero")

    if amount > MAX_SINGLE_TRANSFER_INR:
        raise RiskLimitExceeded(
            f"Transfer amount ₹{amount:,.2f} exceeds single transaction limit of ₹{MAX_SINGLE_TRANSFER_INR:,.2f}"
        )

    if sender_wallet.id == recipient_wallet.id:
        raise SelfTransferNotAllowed("Cannot transfer funds to your own wallet")

    if sender_wallet.status != WalletStatus.ACTIVE:
        raise WalletFrozen("Sender wallet is not active or has been frozen")

    if recipient_wallet.status != WalletStatus.ACTIVE:
        raise WalletFrozen("Recipient wallet is frozen or suspended")
