"""Auth business logic: registration and credential verification."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailAlreadyRegistered, InvalidCredentials, UserBlocked
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    hash_password_async,
    verify_password_async,
)
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import LoginRequest, RegisterRequest


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    if await get_user_by_email(db, data.email):
        raise EmailAlreadyRegistered()

    user = User(
        name=data.name,
        email=data.email,
        password_hash=await hash_password_async(data.password),
        role=UserRole.USER,  # admins are never self-registered
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Two concurrent registrations with the same email: the unique index decides.
        await db.rollback()
        raise EmailAlreadyRegistered()
    await db.refresh(user)

    # Auto-create INR wallet for newly registered user (per architecture plan)
    from app.services import wallet_service, audit_service
    await wallet_service.get_or_create_wallet_for_user(db, user)
    await audit_service.record_audit(
        db=db,
        action="USER_REGISTER",
        entity_type="USER",
        entity_id=str(user.id),
        actor_id=user.id,
        actor_email=user.email,
        details={"name": user.name, "email": user.email},
    )
    await db.commit()
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User:
    user = await get_user_by_email(db, data.email)
    # Always run one bcrypt verification so timing is the same for unknown emails.
    hash_to_check = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_ok = await verify_password_async(data.password, hash_to_check)

    if not user or not password_ok:
        raise InvalidCredentials()
    if user.status == UserStatus.BLOCKED:
        raise UserBlocked()
    return user
