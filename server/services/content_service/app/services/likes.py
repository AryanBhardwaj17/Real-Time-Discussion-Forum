"""Like service — thread and comment like toggles, liker listings."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ValidationError
from shared.logging import get_logger

from app.core.deps import UserContext
from app.models import CommentLike, ThreadLike
from app.core.redis import publish
from app.repositories import LikeRepository, ThreadRepository, CommentRepository
from app.services.helpers import _publish_notification_event, _publish_notification_retraction
from app.services.threads import get_thread_by_id, recalculate_hot_score
from app.services.comments import get_comment_by_id

logger = get_logger(__name__)


async def has_user_liked_thread(db: AsyncSession, thread_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    like = await LikeRepository.find_thread_like(db, user_id, thread_id)
    return like is not None


async def has_user_liked_comment(db: AsyncSession, comment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    like = await LikeRepository.find_comment_like(db, user_id, comment_id)
    return like is not None


async def toggle_thread_like(db: AsyncSession, thread_id: uuid.UUID, user: UserContext) -> tuple[bool, int]:
    thread = await get_thread_by_id(db, thread_id)
    existing = await LikeRepository.find_thread_like(db, user.id, thread_id)

    if existing is not None:
        await LikeRepository.delete_thread_like(db, existing.id)
        await ThreadRepository.decrement_like_count(db, thread_id)
        await db.flush()
        await db.refresh(thread)
        await recalculate_hot_score(db, thread)
        await _publish_notification_retraction(
            user_id=str(thread.author_id), actor_id=str(user.id),
            notification_type="thread_like", reference_id=str(thread_id),
        )
        await publish(f"thread:{thread_id}", {
            "type": "like_update",
            "data": {"thread_id": str(thread_id), "like_count": thread.like_count, "user_id": str(user.id), "liked": False},
        })
        await publish("threads:feed", {
            "type": "like_update",
            "data": {"thread_id": str(thread_id), "like_count": thread.like_count},
        })
        return False, thread.like_count
    else:
        try:
            await LikeRepository.create_thread_like(db, ThreadLike(user_id=user.id, thread_id=thread_id))
            await ThreadRepository.increment_like_count(db, thread_id)
            await db.flush()
        except IntegrityError:
            raise ValidationError("Already liked")
        await db.refresh(thread)
        await recalculate_hot_score(db, thread)
        await _publish_notification_event(
            user_id=str(thread.author_id), actor_id=str(user.id),
            notification_type="thread_like", reference_type="thread",
            reference_id=str(thread_id), thread_id=str(thread_id),
            content=f"@{user.username} liked your thread",
        )
        await publish(f"thread:{thread_id}", {
            "type": "like_update",
            "data": {"thread_id": str(thread_id), "like_count": thread.like_count, "user_id": str(user.id), "liked": True},
        })
        await publish("threads:feed", {
            "type": "like_update",
            "data": {"thread_id": str(thread_id), "like_count": thread.like_count},
        })
        return True, thread.like_count


async def toggle_comment_like(db: AsyncSession, comment_id: uuid.UUID, user: UserContext) -> tuple[bool, int]:
    comment = await get_comment_by_id(db, comment_id)
    existing = await LikeRepository.find_comment_like(db, user.id, comment_id)

    if existing is not None:
        await LikeRepository.delete_comment_like(db, existing.id)
        await CommentRepository.decrement_like_count(db, comment_id)
        await db.flush()
        await db.refresh(comment)
        await _publish_notification_retraction(
            user_id=str(comment.author_id), actor_id=str(user.id),
            notification_type="comment_like", reference_id=str(comment_id),
        )
        await publish(f"thread:{comment.thread_id}", {
            "type": "comment_like_update",
            "data": {"comment_id": str(comment_id), "like_count": comment.like_count, "user_id": str(user.id), "liked": False},
        })
        return False, comment.like_count
    else:
        try:
            await LikeRepository.create_comment_like(db, CommentLike(user_id=user.id, comment_id=comment_id))
            await CommentRepository.increment_like_count(db, comment_id)
            await db.flush()
        except IntegrityError:
            raise ValidationError("Already liked")
        await db.refresh(comment)
        await _publish_notification_event(
            user_id=str(comment.author_id), actor_id=str(user.id),
            notification_type="comment_like", reference_type="comment",
            reference_id=str(comment_id), thread_id=str(comment.thread_id),
            content=f"@{user.username} liked your comment",
        )
        await publish(f"thread:{comment.thread_id}", {
            "type": "comment_like_update",
            "data": {"comment_id": str(comment_id), "like_count": comment.like_count, "user_id": str(user.id), "liked": True},
        })
        return True, comment.like_count


async def list_thread_likers(db: AsyncSession, thread_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
    return await LikeRepository.list_thread_likers(db, thread_id, cursor=cursor, limit=limit)


async def list_comment_likers(db: AsyncSession, comment_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
    return await LikeRepository.list_comment_likers(db, comment_id, cursor=cursor, limit=limit)
