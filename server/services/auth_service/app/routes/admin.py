"""Admin routes — user management, role changes, deactivation/reactivation."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Query

from shared.schemas import CursorPage
from app.core.deps import AdminUser, DbSession
from app.models import UserRole
from app.schemas import RoleUpdate, UserRead
from app import services

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@admin_router.get("/users", response_model=CursorPage[UserRead])
async def list_users(
    db: DbSession,
    admin: AdminUser,
    cursor: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> CursorPage[UserRead]:
    users, next_cursor = await services.list_users(db, cursor=cursor, limit=limit)
    return CursorPage(
        items=[UserRead.model_validate(u) for u in users],
        next_cursor=next_cursor.isoformat() if next_cursor else None,
        has_more=next_cursor is not None,
    )


@admin_router.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, db: DbSession, admin: AdminUser) -> UserRead:
    user = await services.get_user_by_id(db, user_id)
    return UserRead.model_validate(user)


@admin_router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_role(user_id: uuid.UUID, data: RoleUpdate, db: DbSession, admin: AdminUser) -> UserRead:
    new_role = UserRole(data.role)
    user = await services.update_user_role(db, target_user_id=user_id, new_role=new_role, actor=admin)
    return UserRead.model_validate(user)


@admin_router.post("/users/{user_id}/deactivate", response_model=UserRead)
async def deactivate(user_id: uuid.UUID, db: DbSession, admin: AdminUser) -> UserRead:
    user = await services.deactivate_user(db, target_user_id=user_id, actor=admin)
    return UserRead.model_validate(user)


@admin_router.post("/users/{user_id}/reactivate", response_model=UserRead)
async def reactivate(user_id: uuid.UUID, db: DbSession, admin: AdminUser) -> UserRead:
    user = await services.reactivate_user(db, target_user_id=user_id, actor=admin)
    return UserRead.model_validate(user)
