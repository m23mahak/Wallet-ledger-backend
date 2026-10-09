"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.configuration.config import get_settings
from app.configuration.constants import API_V1_PREFIX
from app.core.exceptions import ServiceUnavailable
from app.core.security import hash_password_async
from app.database.base import Base
from app.database.session import AsyncSessionLocal, check_db_connection, engine
from app.middleware.error_middleware import register_exception_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.models.user import User, UserRole, UserStatus
from app.routes import (
    admin as admin_routes,
    auth as auth_routes,
    holds as hold_routes,
    transactions as transaction_routes,
    transfers as transfer_routes,
    wallets as wallet_routes,
)
from app.services import wallet_service

settings = get_settings()

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("walletledger")


async def init_db_and_seed():
    """Ensure database schema is created and initial seed users exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed Admin
        admin_res = await session.execute(select(User).where(User.email == "admin@walletledger.com"))
        admin_user = admin_res.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                name="System Administrator",
                email="admin@walletledger.com",
                password_hash=await hash_password_async("AdminPass123!"),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            await wallet_service.get_or_create_wallet_for_user(session, admin_user)
            logger.info("Created default admin user: admin@walletledger.com")

        # 2. Seed Demo User
        user_res = await session.execute(select(User).where(User.email == "user@walletledger.com"))
        demo_user = user_res.scalar_one_or_none()
        if not demo_user:
            demo_user = User(
                name="Vikramaditya S.",
                email="user@walletledger.com",
                password_hash=await hash_password_async("UserPass123!"),
                role=UserRole.USER,
                status=UserStatus.ACTIVE,
            )
            session.add(demo_user)
            await session.commit()
            await session.refresh(demo_user)
            wallet = await wallet_service.get_or_create_wallet_for_user(session, demo_user)
            # Give demo user initial funds so they can immediately test transfers & holds
            if wallet.balance == 0:
                await wallet_service.deposit_to_wallet(
                    db=session,
                    wallet_id=wallet.id,
                    amount=Decimal("25000.00"),
                    description="Initial Demo Balance",
                    actor_id=demo_user.id,
                    actor_email=demo_user.email,
                )
            logger.info("Created default demo user: user@walletledger.com (with ₹25,000 balance)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (%s)", settings.app_name, settings.environment)
    try:
        await init_db_and_seed()
    except Exception as e:
        logger.warning("Could not auto-seed database: %s", e)
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Digital-wallet backend simulator with a double-entry ledger.",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)

# Default CORS origins fallback if none provided
configured_origins = settings.cors_origin_list
if not configured_origins:
    configured_origins = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

# Include all domain routers
app.include_router(auth_routes.router, prefix=API_V1_PREFIX)
app.include_router(wallet_routes.router, prefix=API_V1_PREFIX)
app.include_router(transfer_routes.router, prefix=API_V1_PREFIX)
app.include_router(hold_routes.router, prefix=API_V1_PREFIX)
app.include_router(transaction_routes.router, prefix=API_V1_PREFIX)
app.include_router(admin_routes.router, prefix=API_V1_PREFIX)


@app.get("/", tags=["General"], summary="API Root")
async def root():
    return {
        "name": settings.app_name,
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "api_v1": API_V1_PREFIX,
    }


@app.get("/health", tags=["Health"], summary="Liveness check")
async def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["Health"], summary="Database connectivity check")
async def health_db():
    try:
        await check_db_connection()
    except Exception:
        logger.exception("Database health check failed")
        raise ServiceUnavailable("Database unavailable")
    return {"status": "ok", "database": "connected"}
