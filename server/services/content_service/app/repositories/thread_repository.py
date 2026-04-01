"""Thread repository — all thread-related data access."""

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Thread, thread_tags_table
from app.services.helpers import _parse_cursor_dt, _parse_cursor_dt_id


class ThreadRepository:
    """Encapsulates all database operations for the Thread model."""

    @staticmethod
    async def find_by_id(db: AsyncSession, thread_id: uuid.UUID, *, include_deleted: bool = False) -> Thread | None:
        stmt = select(Thread).where(Thread.id == thread_id)
        if not include_deleted:
            stmt = stmt.where(Thread.is_deleted.is_(False))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_paginated(db: AsyncSession, *, sort: str = "hot", cursor: str | None = None, limit: int = 20):
        stmt = select(Thread).where(Thread.is_deleted.is_(False), Thread.author_is_active.is_(True))

        if sort == "new":
            stmt = stmt.order_by(Thread.is_pinned.desc(), Thread.created_at.desc(), Thread.id.desc())
            if cursor:
                dt, uid = _parse_cursor_dt_id(cursor)
                stmt = stmt.where(
                    (Thread.created_at < dt)
                    | ((Thread.created_at == dt) & (Thread.id < uid))
                )
        elif sort == "top":
            stmt = stmt.order_by(Thread.is_pinned.desc(), Thread.like_count.desc(), Thread.created_at.desc())
            if cursor:
                parts = cursor.split("|")
                stmt = stmt.where(
                    (Thread.like_count < int(parts[0]))
                    | ((Thread.like_count == int(parts[0])) & (Thread.created_at < _parse_cursor_dt(parts[1])))
                )
        else:
            stmt = stmt.order_by(Thread.is_pinned.desc(), Thread.hot_score.desc(), Thread.created_at.desc())
            if cursor:
                parts = cursor.split("|")
                stmt = stmt.where(
                    (Thread.hot_score < float(parts[0]))
                    | ((Thread.hot_score == float(parts[0])) & (Thread.created_at < _parse_cursor_dt(parts[1])))
                )

        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        threads = list(result.scalars().all())

        next_cursor = None
        if len(threads) > limit:
            threads = threads[:limit]
            last = threads[-1]
            if sort == "new":
                next_cursor = f"{last.created_at.isoformat()}|{last.id}"
            elif sort == "top":
                next_cursor = f"{last.like_count}|{last.created_at.isoformat()}"
            else:
                next_cursor = f"{last.hot_score}|{last.created_at.isoformat()}"

        return threads, next_cursor

    @staticmethod
    async def create(db: AsyncSession, thread: Thread) -> Thread:
        db.add(thread)
        await db.flush()
        return thread

    @staticmethod
    async def increment_comment_count(db: AsyncSession, thread_id: uuid.UUID) -> None:
        await db.execute(
            update(Thread).where(Thread.id == thread_id).values(comment_count=Thread.comment_count + 1)
        )

    @staticmethod
    async def increment_like_count(db: AsyncSession, thread_id: uuid.UUID) -> None:
        await db.execute(
            update(Thread).where(Thread.id == thread_id).values(like_count=Thread.like_count + 1)
        )

    @staticmethod
    async def decrement_like_count(db: AsyncSession, thread_id: uuid.UUID) -> None:
        await db.execute(
            update(Thread).where(Thread.id == thread_id).values(like_count=Thread.like_count - 1)
        )

    @staticmethod
    async def set_tag_associations(db: AsyncSession, thread_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
        await db.execute(delete(thread_tags_table).where(thread_tags_table.c.thread_id == thread_id))
        for tag_id in tag_ids:
            await db.execute(thread_tags_table.insert().values(thread_id=thread_id, tag_id=tag_id))

    @staticmethod
    async def count_by_author(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(Thread.id)).where(Thread.author_id == user_id, Thread.is_deleted.is_(False))
        )
        return result.scalar_one()

    @staticmethod
    async def count_active(db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(Thread.id)).where(Thread.is_deleted.is_(False))
        )
        return result.scalar_one()

    @staticmethod
    async def list_by_author(db: AsyncSession, user_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
        stmt = select(Thread).where(Thread.author_id == user_id, Thread.is_deleted.is_(False)).order_by(Thread.created_at.desc())
        if cursor:
            stmt = stmt.where(Thread.created_at < _parse_cursor_dt(cursor))
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        threads = list(result.scalars().all())

        next_cursor = None
        if len(threads) > limit:
            threads = threads[:limit]
            next_cursor = threads[-1].created_at.isoformat()
        return threads, next_cursor

    @staticmethod
    async def sum_likes_by_author(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(Thread.like_count), 0))
            .where(Thread.author_id == user_id, Thread.is_deleted.is_(False))
        )
        return result.scalar_one()

    @staticmethod
    async def list_recent(db: AsyncSession, *, since: datetime, limit: int = 20):
        result = await db.execute(
            select(Thread).where(Thread.is_deleted.is_(False), Thread.created_at >= since)
            .order_by(Thread.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
