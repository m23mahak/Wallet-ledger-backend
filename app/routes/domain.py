from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database.session import get_db
from app.schemas.domain import UserCreate, UserResponse, WalletCreate, WalletResponse, TransactionCreate, TransactionResponse
from app.services.domain import create_user, get_user_by_username, create_wallet, get_wallets, create_transaction

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await create_user(db, user_in)

@router.post("/wallets", response_model=WalletResponse)
async def add_wallet(user_id: str, wallet_in: WalletCreate, db: AsyncSession = Depends(get_db)):
    return await create_wallet(db, user_id, wallet_in)

@router.get("/wallets", response_model=List[WalletResponse])
async def list_wallets(user_id: str, db: AsyncSession = Depends(get_db)):
    return await get_wallets(db, user_id)

@router.post("/transactions", response_model=TransactionResponse)
async def transfer_money(from_wallet_id: str, tx_in: TransactionCreate, db: AsyncSession = Depends(get_db)):
    return await create_transaction(db, from_wallet_id, tx_in)
