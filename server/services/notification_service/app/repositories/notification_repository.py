"""Notification repository — all notification data access."""

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


class NotificationRepository:
    """Encapsulates all database operations for the Notification model."""

    @staticmethod
    async def list_for_user(
        db: AsyncSession, user_id: uuid.UUID, *,
        unread_only: bool = False, cursor: str | None = None, limit: int = 30,
    ):
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
        if cursor:
            parts = cursor.split("|", 1)
            if len(parts) == 2:
                dt = datetime.fromisoformat(parts[0].replace(" ", "+"))
                uid = uuid.UUID(parts[1])
                stmt = stmt.where(
                    (Notification.created_at < dt)
                    | ((Notification.created_at == dt) & (Notification.id < uid))
                )
            else:
                stmt = stmt.where(
                    Notification.created_at < datetime.fromisoformat(cursor.replace(" ", "+"))
                )
        stmt = stmt.limit(limit + 1)

        result = await db.execute(stmt)
        notifications = list(result.scalars().all())

        next_cursor = None
        if len(notifications) > limit:
            notifications = notifications[:limit]
            next_cursor = f"{notifications[-1].created_at.isoformat()}|{notifications[-1].id}"

        return notifications, next_cursor

    @staticmethod
    async def count_unread(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.is_read.is_(False),
            )
        )
        return result.scalar_one()

    @staticmethod
    async def mark_read(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        return result.rowcount
