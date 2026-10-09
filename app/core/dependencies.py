"""Reusable FastAPI dependencies: DB session, current user, current admin."""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, Unauthorized, UserBlocked
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User, UserRole, UserStatus
from app.services import auth_service

# auto_error=False so a missing header returns OUR error envelope, not FastAPI's default.
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise Unauthorized("Missing authentication token")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise Unauthorized("Invalid or expired token")

    # Always re-load from the DB: role/status changes take effect immediately.
    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise Unauthorized("Invalid or expired token")
    if user.status == UserStatus.BLOCKED:
        raise UserBlocked()
    return user


async def get_current_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.ADMIN:
        raise Forbidden("Admin access required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
