"""Auth routes — registration, login, tokens, password management."""

from fastapi import APIRouter

from shared.schemas import MessageResponse
from app.core.deps import CurrentUser, DbSession
from app.schemas import (
    ChangePassword, RefreshTokenRequest,
    TokenPair, UserCreate, UserLogin, UserRead,
)
from app import services

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, db: DbSession) -> UserRead:
    user = await services.create_user(db, data)
    return UserRead.model_validate(user)


@auth_router.post("/login", response_model=TokenPair)
async def login(data: UserLogin, db: DbSession) -> TokenPair:
    user = await services.authenticate_user(db, data.login, data.password)
    pair = await services.create_token_pair(db, user)
    return TokenPair(**pair)


@auth_router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshTokenRequest, db: DbSession) -> TokenPair:
    pair = await services.rotate_refresh_token(db, data.refresh_token)
    return TokenPair(**pair)


@auth_router.post("/logout", response_model=MessageResponse)
async def logout(data: RefreshTokenRequest, db: DbSession) -> MessageResponse:
    await services.revoke_refresh_token(db, data.refresh_token)
    return MessageResponse(message="Successfully logged out")


@auth_router.post("/change-password", response_model=MessageResponse)
async def change_password_route(data: ChangePassword, db: DbSession, user: CurrentUser) -> MessageResponse:
    await services.change_password(db, user, data.current_password, data.new_password)
    return MessageResponse(message="Password changed successfully")
