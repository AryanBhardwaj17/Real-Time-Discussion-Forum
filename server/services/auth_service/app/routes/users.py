"""User routes — profile, deactivation, deletion."""

from fastapi import APIRouter

from shared.schemas import MessageResponse
from app.core.deps import CurrentUser, DbSession
from app.schemas import PublicUserRead, UserRead, UserUpdate
from app import services

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@users_router.patch("/me", response_model=UserRead)
async def update_me(data: UserUpdate, db: DbSession, user: CurrentUser) -> UserRead:
    updated = await services.update_user_profile(db, user, data)
    return UserRead.model_validate(updated)


@users_router.patch("/me/deactivate", response_model=MessageResponse)
async def deactivate_me(db: DbSession, user: CurrentUser) -> MessageResponse:
    """Soft-delete: disable the account while preserving all data."""
    await services.deactivate_own_account(db, user)
    return MessageResponse(message="Account deactivated. Contact support to reactivate.")


@users_router.delete("/me", response_model=MessageResponse)
async def delete_me(db: DbSession, user: CurrentUser) -> MessageResponse:
    """Hard-delete: permanently remove the account and all tokens."""
    await services.delete_own_account(db, user)
    return MessageResponse(message="Account permanently deleted.")


@users_router.get("/{username}", response_model=PublicUserRead)
async def get_public_profile(username: str, db: DbSession) -> PublicUserRead:
    user = await services.get_user_by_username(db, username)
    return PublicUserRead.model_validate(user)
