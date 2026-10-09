"""Auth endpoints. No business logic here."""
from fastapi import APIRouter, status

from app.controllers import auth_controller
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import ErrorResponse, SuccessResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a USER account. Email is normalized to lowercase and must be unique.",
    responses={409: {"model": ErrorResponse, "description": "Email already registered"}},
)
async def register(payload: RegisterRequest, db: DbSession):
    return SuccessResponse(data=await auth_controller.register(db, payload))


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Log in and receive a JWT access token",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        403: {"model": ErrorResponse, "description": "Account blocked"},
    },
)
async def login(payload: LoginRequest, db: DbSession):
    return SuccessResponse(data=await auth_controller.login(db, payload))


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get the authenticated user",
    responses={401: {"model": ErrorResponse, "description": "Missing or invalid token"}},
)
async def me(user: CurrentUser):
    return SuccessResponse(data=auth_controller.me(user))
