"""Reconciliation service for double-entry ledger audits and balance integrity verification."""
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.wallet import Wallet


async def run_reconciliation(db: AsyncSession) -> dict:
    # 1. Total debits and credits across the entire ledger
    debit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
        LedgerEntry.entry_type == LedgerEntryType.DEBIT
    )
    credit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
        LedgerEntry.entry_type == LedgerEntryType.CREDIT
    )

    total_debits = Decimal(str((await db.execute(debit_stmt)).scalar() or 0))
    total_credits = Decimal(str((await db.execute(credit_stmt)).scalar() or 0))
    net_diff = total_credits - total_debits

    # 2. Check each wallet's balance against its ledger entries
    wallets_stmt = select(Wallet)
    wallets = list((await db.execute(wallets_stmt)).scalars().all())

    checked_count = len(wallets)
    discrepancy_count = 0
    details = []

    if net_diff != Decimal("0.00"):
        details.append(
            f"System Ledger Imbalance: Total Credits (₹{total_credits:,.2f}) != Total Debits (₹{total_debits:,.2f}), Difference = ₹{net_diff:,.2f}"
        )
    else:
        details.append("System Double-Entry Ledger: Balanced (Debits equal Credits).")

    for w in wallets:
        # Sum credits to this wallet
        w_credit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.wallet_id == w.id,
            LedgerEntry.entry_type == LedgerEntryType.CREDIT,
        )
        # Sum debits from this wallet
        w_debit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.wallet_id == w.id,
            LedgerEntry.entry_type == LedgerEntryType.DEBIT,
        )

        w_credits = Decimal(str((await db.execute(w_credit_stmt)).scalar() or 0))
        w_debits = Decimal(str((await db.execute(w_debit_stmt)).scalar() or 0))
        ledger_expected_balance = w_credits - w_debits

        if w.balance != ledger_expected_balance:
            discrepancy_count += 1
            details.append(
                f"Discrepancy on Wallet {w.wallet_number}: Stored balance ₹{w.balance:,.2f} != Ledger balance ₹{ledger_expected_balance:,.2f}"
            )

    if discrepancy_count == 0 and net_diff == Decimal("0.00"):
        status = "BALANCED"
        details.append(f"All {checked_count} wallets verified successfully against immutable ledger.")
    else:
        status = "DISCREPANCY"

    return {
        "status": status,
        "total_debits": float(total_debits),
        "total_credits": float(total_credits),
        "net_system_balance": float(net_diff),
        "checked_wallets": checked_count,
        "discrepant_wallets": discrepancy_count,
        "details": details,
    }
