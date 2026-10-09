"""HTTP-level handling for auth: call services, shape responses."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.configuration.config import get_settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth_service


async def register(db: AsyncSession, payload: RegisterRequest) -> UserResponse:
    user = await auth_service.register_user(db, payload)
    return UserResponse.model_validate(user)


async def login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    user = await auth_service.authenticate_user(db, payload)
    expires = get_settings().access_token_expire_minutes
    token = create_access_token(user.id, user.role.value, expires)
    
    from app.services import audit_service
    await audit_service.record_audit(
        db=db,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=str(user.id),
        actor_id=user.id,
        actor_email=user.email,
    )
    await db.commit()
    return TokenResponse(access_token=token, expires_in=expires * 60)


def me(user: User) -> UserResponse:
    return UserResponse.model_validate(user)
