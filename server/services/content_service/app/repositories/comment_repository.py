"""Comment repository — all comment-related data access."""

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment
from app.services.helpers import _parse_cursor_dt, _parse_cursor_dt_id


class CommentRepository:
    """Encapsulates all database operations for the Comment model."""

    @staticmethod
    async def find_by_id(db: AsyncSession, comment_id: uuid.UUID) -> Comment | None:
        result = await db.execute(select(Comment).where(Comment.id == comment_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_top_level(db: AsyncSession, thread_id: uuid.UUID, *, sort: str = "new", cursor: str | None = None, limit: int = 50):
        stmt = select(Comment).where(Comment.thread_id == thread_id, Comment.parent_id.is_(None))

        if sort == "old":
            stmt = stmt.order_by(Comment.created_at.asc(), Comment.id.asc())
            if cursor:
                dt, uid = _parse_cursor_dt_id(cursor)
                stmt = stmt.where(
                    (Comment.created_at > dt)
                    | ((Comment.created_at == dt) & (Comment.id > uid))
                )
        elif sort == "top":
            stmt = stmt.order_by(Comment.like_count.desc(), Comment.created_at.desc())
            if cursor:
                parts = cursor.split("|")
                stmt = stmt.where(
                    (Comment.like_count < int(parts[0]))
                    | ((Comment.like_count == int(parts[0])) & (Comment.created_at < _parse_cursor_dt(parts[1])))
                )
        else:
            stmt = stmt.order_by(Comment.created_at.desc(), Comment.id.desc())
            if cursor:
                dt, uid = _parse_cursor_dt_id(cursor)
                stmt = stmt.where(
                    (Comment.created_at < dt)
                    | ((Comment.created_at == dt) & (Comment.id < uid))
                )

        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        comments = list(result.scalars().all())

        next_cursor = None
        if len(comments) > limit:
            comments = comments[:limit]
            last = comments[-1]
            if sort == "old":
                next_cursor = f"{last.created_at.isoformat()}|{last.id}"
            elif sort == "top":
                next_cursor = f"{last.like_count}|{last.created_at.isoformat()}"
            else:
                next_cursor = f"{last.created_at.isoformat()}|{last.id}"

        return comments, next_cursor

    @staticmethod
    async def list_replies(db: AsyncSession, parent_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
        stmt = select(Comment).where(Comment.parent_id == parent_id).order_by(Comment.created_at.asc(), Comment.id.asc())
        if cursor:
            dt, uid = _parse_cursor_dt_id(cursor)
            stmt = stmt.where(
                (Comment.created_at > dt)
                | ((Comment.created_at == dt) & (Comment.id > uid))
            )
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        replies = list(result.scalars().all())

        next_cursor = None
        if len(replies) > limit:
            replies = replies[:limit]
            next_cursor = f"{replies[-1].created_at.isoformat()}|{replies[-1].id}"

        return replies, next_cursor

    @staticmethod
    async def create(db: AsyncSession, comment: Comment) -> Comment:
        db.add(comment)
        await db.flush()
        return comment

    @staticmethod
    async def increment_reply_count(db: AsyncSession, comment_id: uuid.UUID) -> None:
        await db.execute(
            update(Comment).where(Comment.id == comment_id).values(reply_count=Comment.reply_count + 1)
        )

    @staticmethod
    async def increment_like_count(db: AsyncSession, comment_id: uuid.UUID) -> None:
        await db.execute(
            update(Comment).where(Comment.id == comment_id).values(like_count=Comment.like_count + 1)
        )

    @staticmethod
    async def decrement_like_count(db: AsyncSession, comment_id: uuid.UUID) -> None:
        await db.execute(
            update(Comment).where(Comment.id == comment_id).values(like_count=Comment.like_count - 1)
        )

    @staticmethod
    async def count_by_author(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(Comment.id)).where(Comment.author_id == user_id, Comment.is_deleted.is_(False))
        )
        return result.scalar_one()

    @staticmethod
    async def count_active(db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(Comment.id)).where(Comment.is_deleted.is_(False))
        )
        return result.scalar_one()

    @staticmethod
    async def list_by_author(db: AsyncSession, user_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
        stmt = select(Comment).where(Comment.author_id == user_id, Comment.is_deleted.is_(False)).order_by(Comment.created_at.desc())
        if cursor:
            stmt = stmt.where(Comment.created_at < _parse_cursor_dt(cursor))
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        comments = list(result.scalars().all())

        next_cursor = None
        if len(comments) > limit:
            comments = comments[:limit]
            next_cursor = comments[-1].created_at.isoformat()
        return comments, next_cursor

    @staticmethod
    async def sum_likes_by_author(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(Comment.like_count), 0))
            .where(Comment.author_id == user_id, Comment.is_deleted.is_(False))
        )
        return result.scalar_one()

    @staticmethod
    async def list_recent(db: AsyncSession, *, since: datetime, limit: int = 20):
        result = await db.execute(
            select(Comment).where(Comment.is_deleted.is_(False), Comment.created_at >= since)
            .order_by(Comment.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
