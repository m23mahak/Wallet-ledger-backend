from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.domain import User, Wallet, Transaction, LedgerEntry, Hold, TransactionStatus
from app.schemas.domain import UserCreate, WalletCreate, TransactionCreate, HoldCreate

async def create_user(db: AsyncSession, user_in: UserCreate):
    user = User(username=user_in.username, hashed_password=user_in.password + "_hashed")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_wallet(db: AsyncSession, user_id: str, wallet_in: WalletCreate):
    wallet = Wallet(user_id=user_id, currency=wallet_in.currency)
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)
    return wallet

async def get_wallets(db: AsyncSession, user_id: str):
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    return result.scalars().all()

async def create_transaction(db: AsyncSession, from_wallet_id: str, tx_in: TransactionCreate):
    tx = Transaction(from_wallet_id=from_wallet_id, to_wallet_id=tx_in.to_wallet_id, amount=tx_in.amount, status=TransactionStatus.COMPLETED)
    db.add(tx)
    
    if from_wallet_id:
        le1 = LedgerEntry(transaction_id=tx.id, wallet_id=from_wallet_id, amount=-tx_in.amount)
        db.add(le1)
        wallet = await db.execute(select(Wallet).where(Wallet.id == from_wallet_id))
        wallet = wallet.scalars().first()
        if wallet:
            wallet.balance -= tx_in.amount
            
    if tx_in.to_wallet_id:
        le2 = LedgerEntry(transaction_id=tx.id, wallet_id=tx_in.to_wallet_id, amount=tx_in.amount)
        db.add(le2)
        wallet2 = await db.execute(select(Wallet).where(Wallet.id == tx_in.to_wallet_id))
        wallet2 = wallet2.scalars().first()
        if wallet2:
            wallet2.balance += tx_in.amount

    await db.commit()
    await db.refresh(tx)
    return tx
