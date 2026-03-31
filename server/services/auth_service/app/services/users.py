"""User profile service — CRUD, deactivation, deletion."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ConflictError, NotFoundError, ValidationError
from shared.logging import get_logger

from app.models import User
from app.repositories import UserRepository, TokenRepository
from app.services.helpers import _publish_user_status_change

logger = get_logger(__name__)


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await UserRepository.find_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User:
    user = await UserRepository.find_by_username(db, username, active_only=True)
    if user is None:
        raise NotFoundError("User not found")
    return user


async def update_user_profile(db: AsyncSession, user: User, data) -> User:
    update_data = data.model_dump(exclude_unset=True)
    old_username = user.username

    # Check for duplicate username before flushing
    new_username = update_data.get("username")
    if new_username and new_username != old_username:
        dup = await UserRepository.find_duplicate_username(db, new_username, user.id)
        if dup is not None:
            raise ConflictError("Username already taken")

    for field, value in update_data.items():
        setattr(user, field, value)
    try:
        await db.flush()
    except IntegrityError:
        raise ConflictError("Username or email already in use")
    await db.refresh(user)

    # If username changed, publish event so content service can update denormalized copies
    new_username = update_data.get("username")
    if new_username and new_username != old_username:
        try:
            from app.core.redis import stream_add
            await stream_add("stream:user_updates", {
                "event": "username_changed",
                "user_id": str(user.id),
                "old_username": old_username,
                "new_username": new_username,
            })
        except Exception:
            logger.exception("failed_to_publish_username_change", user_id=str(user.id))

    return user


async def deactivate_own_account(db: AsyncSession, user: User) -> None:
    """Soft-delete: mark account inactive and revoke all active tokens."""
    if not user.is_active:
        raise ValidationError("Account is already deactivated")

    user.is_active = False
    user.deactivated_by_admin = False
    await TokenRepository.revoke_all_user_refresh(db, user.id)
    await db.flush()
    await _publish_user_status_change(user.id, False)
    logger.info("user_self_deactivated", user_id=str(user.id))


async def delete_own_account(db: AsyncSession, user: User) -> None:
    """Hard-delete: revoke all tokens then permanently remove the user record."""
    user_id = str(user.id)
    await TokenRepository.revoke_all_user_refresh(db, user.id)
    await _publish_user_status_change(user.id, False)
    await db.delete(user)
    await db.flush()
    logger.info("user_self_deleted", user_id=user_id)
