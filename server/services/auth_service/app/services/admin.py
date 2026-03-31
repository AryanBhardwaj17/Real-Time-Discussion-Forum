"""Admin service — user management, role changes, deactivation/reactivation."""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import NotFoundError, ValidationError
from shared.logging import get_logger

from app.models import User, UserRole
from app.repositories import UserRepository, TokenRepository
from app.services.helpers import _publish_audit_event, _publish_user_status_change
from app.services.users import get_user_by_id

logger = get_logger(__name__)


async def list_users(db: AsyncSession, *, cursor: datetime | None = None, limit: int = 20):
    return await UserRepository.list_paginated(db, cursor=cursor, limit=limit)


async def update_user_role(db: AsyncSession, *, target_user_id: uuid.UUID, new_role: UserRole, actor: User) -> User:
    target = await get_user_by_id(db, target_user_id)
    if target.id == actor.id:
        raise ValidationError("Cannot change your own role")

    old_role = target.role
    target.role = new_role.value

    # Publish audit event via Redis
    await _publish_audit_event(actor.id, "change_role", "user", target.id, {"old_role": old_role, "new_role": new_role.value})

    # Notify the user's active WebSocket so the frontend refreshes tokens + context
    try:
        from app.core.redis import publish
        await publish(f"user:{target.id}", {"type": "role_changed", "new_role": new_role.value})
    except Exception:
        logger.warning("failed_to_publish_role_change", user_id=str(target.id))

    await db.flush()
    await db.refresh(target)
    return target


async def _revoke_all_user_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    await TokenRepository.revoke_all_user_refresh(db, user_id)


async def deactivate_user(db: AsyncSession, *, target_user_id: uuid.UUID, actor: User) -> User:
    target = await get_user_by_id(db, target_user_id)
    if target.id == actor.id:
        raise ValidationError("Cannot deactivate your own account")
    if not target.is_active:
        raise ValidationError("User is already deactivated")

    target.is_active = False
    target.deactivated_by_admin = True
    await _revoke_all_user_tokens(db, target.id)
    await _publish_audit_event(actor.id, "deactivate_user", "user", target.id, {})
    await _publish_user_status_change(target.id, False)
    await db.flush()
    await db.refresh(target)
    return target


async def reactivate_user(db: AsyncSession, *, target_user_id: uuid.UUID, actor: User) -> User:
    target = await get_user_by_id(db, target_user_id)
    if target.is_active:
        raise ValidationError("User is already active")
    target.is_active = True
    target.deactivated_by_admin = False
    await _publish_audit_event(actor.id, "reactivate_user", "user", target.id, {})
    await _publish_user_status_change(target.id, True)
    await db.flush()
    await db.refresh(target)
    return target
