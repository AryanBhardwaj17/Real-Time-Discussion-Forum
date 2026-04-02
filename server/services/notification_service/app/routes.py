"""Notification service routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import UnauthorizedError
from shared.schemas import CursorPage, MessageResponse
from app.db import get_db
from app.repositories import NotificationRepository
from app.schemas import NotificationRead, UnreadCountResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


async def _get_user_id(request: Request) -> uuid.UUID:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise UnauthorizedError("Authentication required")
    return uuid.UUID(user_id)


DbSession = Annotated[AsyncSession, Depends(get_db)]
UserId = Annotated[uuid.UUID, Depends(_get_user_id)]


@router.get("", response_model=CursorPage[NotificationRead])
async def list_notifications(
    db: DbSession, user_id: UserId,
    unread_only: bool = Query(False),
    cursor: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
) -> CursorPage[NotificationRead]:
    notifications, next_cursor = await NotificationRepository.list_for_user(
        db, user_id, unread_only=unread_only, cursor=cursor, limit=limit,
    )
    return CursorPage(
        items=[NotificationRead.model_validate(n) for n in notifications],
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(db: DbSession, user_id: UserId) -> UnreadCountResponse:
    count = await NotificationRepository.count_unread(db, user_id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=MessageResponse)
async def mark_read(notification_id: uuid.UUID, db: DbSession, user_id: UserId) -> MessageResponse:
    await NotificationRepository.mark_read(db, notification_id, user_id)
    return MessageResponse(message="Notification marked as read")


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(db: DbSession, user_id: UserId) -> MessageResponse:
    updated = await NotificationRepository.mark_all_read(db, user_id)
    return MessageResponse(message=f"{updated} notifications marked as read")
