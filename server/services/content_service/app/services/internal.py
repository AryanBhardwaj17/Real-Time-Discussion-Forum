"""Internal service — stats, user content, activity, reindex, counter reconciliation."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging import get_logger

from app.models import Comment, CommentLike, Report, Thread, ThreadLike
from app.repositories import ThreadRepository, CommentRepository, ReportRepository
from app.services.helpers import _parse_cursor_dt, _thread_to_meili_doc

logger = get_logger(__name__)


async def get_content_stats(db: AsyncSession) -> dict:
    """Return aggregate content stats for the dashboard service."""
    total_threads = await ThreadRepository.count_active(db)
    total_comments = await CommentRepository.count_active(db)
    pending_reports = await ReportRepository.count_pending(db)

    return {"total_threads": total_threads, "total_comments": total_comments, "pending_reports": pending_reports}


async def get_user_threads(db: AsyncSession, user_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
    return await ThreadRepository.list_by_author(db, user_id, cursor=cursor, limit=limit)


async def get_user_comments(db: AsyncSession, user_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
    return await CommentRepository.list_by_author(db, user_id, cursor=cursor, limit=limit)


async def get_user_content_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    thread_count = await ThreadRepository.count_by_author(db, user_id)
    comment_count = await CommentRepository.count_by_author(db, user_id)
    thread_likes = await ThreadRepository.sum_likes_by_author(db, user_id)
    comment_likes = await CommentRepository.sum_likes_by_author(db, user_id)
    return {"thread_count": thread_count, "comment_count": comment_count, "likes_received": thread_likes + comment_likes}


async def get_recent_activity(db: AsyncSession, *, hours: int = 24, limit: int = 20) -> dict:
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    threads = await ThreadRepository.list_recent(db, since=since, limit=limit)
    comments = await CommentRepository.list_recent(db, since=since, limit=limit)

    return {
        "recent_threads": [
            {"id": str(t.id), "title": t.title, "author_username": t.author_username,
             "like_count": t.like_count, "comment_count": t.comment_count, "created_at": t.created_at.isoformat()}
            for t in threads
        ],
        "recent_comments": [
            {"id": str(c.id), "content": c.content[:200], "author_username": c.author_username,
             "thread_id": str(c.thread_id), "like_count": c.like_count, "created_at": c.created_at.isoformat()}
            for c in comments
        ],
    }


async def reindex_all_threads(db: AsyncSession) -> int:
    """Re-index all non-deleted threads into Meilisearch (full documents)."""
    result = await db.execute(select(Thread).where(Thread.is_deleted.is_(False)))
    threads = result.scalars().all()
    docs = [_thread_to_meili_doc(t) for t in threads]
    if docs:
        from app.core.meilisearch import get_meili, THREADS_INDEX
        client = get_meili()
        index = client.index(THREADS_INDEX)
        await index.add_documents(docs)
    logger.info("reindex_complete", count=len(docs))
    return len(docs)


async def reconcile_counters(db: AsyncSession) -> dict[str, int]:
    """Reconcile denormalized like/comment/reply counts against actual rows."""
    fixed = {"thread_likes": 0, "thread_comments": 0, "comment_likes": 0, "comment_replies": 0}

    # Thread like_count
    subq = (
        select(ThreadLike.thread_id, func.count().label("cnt"))
        .group_by(ThreadLike.thread_id)
        .subquery()
    )
    stale = await db.execute(
        select(Thread.id, Thread.like_count, subq.c.cnt)
        .outerjoin(subq, Thread.id == subq.c.thread_id)
        .where(Thread.like_count != func.coalesce(subq.c.cnt, 0))
    )
    for tid, _old, actual in stale.all():
        await db.execute(update(Thread).where(Thread.id == tid).values(like_count=actual or 0))
        fixed["thread_likes"] += 1

    # Thread comment_count
    subq = (
        select(Comment.thread_id, func.count().label("cnt"))
        .where(Comment.is_deleted.is_(False))
        .group_by(Comment.thread_id)
        .subquery()
    )
    stale = await db.execute(
        select(Thread.id, Thread.comment_count, subq.c.cnt)
        .outerjoin(subq, Thread.id == subq.c.thread_id)
        .where(Thread.comment_count != func.coalesce(subq.c.cnt, 0))
    )
    for tid, _old, actual in stale.all():
        await db.execute(update(Thread).where(Thread.id == tid).values(comment_count=actual or 0))
        fixed["thread_comments"] += 1

    # Comment like_count
    subq = (
        select(CommentLike.comment_id, func.count().label("cnt"))
        .group_by(CommentLike.comment_id)
        .subquery()
    )
    stale = await db.execute(
        select(Comment.id, Comment.like_count, subq.c.cnt)
        .outerjoin(subq, Comment.id == subq.c.comment_id)
        .where(Comment.like_count != func.coalesce(subq.c.cnt, 0))
    )
    for cid, _old, actual in stale.all():
        await db.execute(update(Comment).where(Comment.id == cid).values(like_count=actual or 0))
        fixed["comment_likes"] += 1

    # Comment reply_count
    subq = (
        select(Comment.parent_id, func.count().label("cnt"))
        .where(Comment.is_deleted.is_(False), Comment.parent_id.isnot(None))
        .group_by(Comment.parent_id)
        .subquery()
    )
    stale = await db.execute(
        select(Comment.id, Comment.reply_count, subq.c.cnt)
        .outerjoin(subq, Comment.id == subq.c.parent_id)
        .where(Comment.reply_count != func.coalesce(subq.c.cnt, 0))
    )
    for cid, _old, actual in stale.all():
        await db.execute(update(Comment).where(Comment.id == cid).values(reply_count=actual or 0))
        fixed["comment_replies"] += 1

    await db.flush()
    return fixed
