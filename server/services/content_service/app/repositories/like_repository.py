"""Like repository — ThreadLike and CommentLike data access."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CommentLike, ThreadLike
from app.services.helpers import _parse_cursor_dt_id


class LikeRepository:
    """Encapsulates all database operations for like models."""

    # ── Thread Likes ─────────────────────────────────────────────

    @staticmethod
    async def find_thread_like(db: AsyncSession, user_id: uuid.UUID, thread_id: uuid.UUID) -> ThreadLike | None:
        result = await db.execute(
            select(ThreadLike).where(ThreadLike.user_id == user_id, ThreadLike.thread_id == thread_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_thread_like(db: AsyncSession, like: ThreadLike) -> ThreadLike:
        db.add(like)
        await db.flush()
        return like

    @staticmethod
    async def delete_thread_like(db: AsyncSession, like_id: uuid.UUID) -> None:
        await db.execute(delete(ThreadLike).where(ThreadLike.id == like_id))

    @staticmethod
    async def list_thread_likers(db: AsyncSession, thread_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
        stmt = (
            select(ThreadLike)
            .where(ThreadLike.thread_id == thread_id)
            .order_by(ThreadLike.created_at.desc(), ThreadLike.id.desc())
        )
        if cursor:
            dt, uid = _parse_cursor_dt_id(cursor)
            stmt = stmt.where(
                (ThreadLike.created_at < dt)
                | ((ThreadLike.created_at == dt) & (ThreadLike.id < uid))
            )
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        likes = list(result.scalars().all())

        next_cursor = None
        if len(likes) > limit:
            likes = likes[:limit]
            next_cursor = f"{likes[-1].created_at.isoformat()}|{likes[-1].id}"

        return likes, next_cursor

    # ── Comment Likes ────────────────────────────────────────────

    @staticmethod
    async def find_comment_like(db: AsyncSession, user_id: uuid.UUID, comment_id: uuid.UUID) -> CommentLike | None:
        result = await db.execute(
            select(CommentLike).where(CommentLike.user_id == user_id, CommentLike.comment_id == comment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_comment_like(db: AsyncSession, like: CommentLike) -> CommentLike:
        db.add(like)
        await db.flush()
        return like

    @staticmethod
    async def delete_comment_like(db: AsyncSession, like_id: uuid.UUID) -> None:
        await db.execute(delete(CommentLike).where(CommentLike.id == like_id))

    @staticmethod
    async def list_comment_likers(db: AsyncSession, comment_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
        stmt = (
            select(CommentLike)
            .where(CommentLike.comment_id == comment_id)
            .order_by(CommentLike.created_at.desc(), CommentLike.id.desc())
        )
        if cursor:
            dt, uid = _parse_cursor_dt_id(cursor)
            stmt = stmt.where(
                (CommentLike.created_at < dt)
                | ((CommentLike.created_at == dt) & (CommentLike.id < uid))
            )
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        likes = list(result.scalars().all())

        next_cursor = None
        if len(likes) > limit:
            likes = likes[:limit]
            next_cursor = f"{likes[-1].created_at.isoformat()}|{likes[-1].id}"

        return likes, next_cursor
