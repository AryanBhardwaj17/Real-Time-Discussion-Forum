"""Comment service — CRUD, masking for deleted/deactivated authors."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ForbiddenError, NotFoundError, ValidationError
from shared.logging import get_logger

from app.core.deps import UserContext
from app.models import Comment, Thread
from app.core.redis import publish
from app.repositories import CommentRepository, ThreadRepository
from app.services.helpers import (
    _can_moderate,
    _parse_cursor_dt,
    _parse_cursor_dt_id,
    _publish_audit_event,
    _publish_notification_event,
    _sanitize,
    _send_mention_notifications,
)

logger = get_logger(__name__)


async def get_comment_by_id(db, comment_id: uuid.UUID) -> Comment:
    comment = await CommentRepository.find_by_id(db, comment_id)
    if comment is None or comment.is_deleted:
        raise NotFoundError("Comment not found")
    return comment


async def list_comments(db, thread_id: uuid.UUID, *, sort: str = "new", cursor: str | None = None, limit: int = 50):
    return await CommentRepository.list_top_level(db, thread_id, sort=sort, cursor=cursor, limit=limit)


async def list_replies(db, parent_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20):
    return await CommentRepository.list_replies(db, parent_id, cursor=cursor, limit=limit)


async def create_comment(db, thread_id: uuid.UUID, data, user: UserContext) -> Comment:
    thread = await ThreadRepository.find_by_id(db, thread_id)
    if thread is None:
        raise NotFoundError("Thread not found")
    if thread.is_locked:
        raise ForbiddenError("Thread is locked")

    depth = 0
    if data.parent_id is not None:
        parent = await get_comment_by_id(db, data.parent_id)
        if parent.thread_id != thread_id:
            raise ValidationError("Parent comment does not belong to this thread")
        if parent.is_deleted:
            raise ValidationError("Cannot reply to a deleted comment")
        depth = parent.depth + 1
        if depth > 10:
            raise ValidationError("Maximum comment depth exceeded")

    comment = Comment(
        content=_sanitize(data.content),
        thread_id=thread_id,
        author_id=user.id,
        author_username=user.username,
        author_role=user.role,
        parent_id=data.parent_id,
        depth=depth,
    )
    await CommentRepository.create(db, comment)
    await ThreadRepository.increment_comment_count(db, thread_id)

    if data.parent_id is not None:
        await CommentRepository.increment_reply_count(db, data.parent_id)

    await db.flush()

    # Publish notification event via Redis (notification service handles delivery)
    if data.parent_id is not None:
        parent = await get_comment_by_id(db, data.parent_id)
        await _publish_notification_event(
            user_id=str(parent.author_id), actor_id=str(user.id),
            notification_type="reply", reference_type="comment",
            reference_id=str(comment.id), thread_id=str(thread_id),
            content=f"@{user.username} replied to your comment",
        )
    else:
        await _publish_notification_event(
            user_id=str(thread.author_id), actor_id=str(user.id),
            notification_type="reply", reference_type="thread",
            reference_id=str(thread.id), thread_id=str(thread.id),
            content=f"@{user.username} commented on your thread",
        )

    # Mention notifications
    await _send_mention_notifications(
        text=data.content, actor=user,
        reference_type="comment", reference_id=str(comment.id),
        thread_id=str(thread_id),
        exclude_user_ids={str(user.id), str(thread.author_id)} | ({str(parent.author_id)} if data.parent_id else set()),
    )

    # Broadcast new comment to thread room
    await publish(f"thread:{thread_id}", {
        "type": "new_comment",
        "data": {
            "id": str(comment.id), "content": comment.content, "thread_id": str(thread_id),
            "author_id": str(user.id), "author_username": user.username,
            "parent_id": str(comment.parent_id) if comment.parent_id else None,
            "depth": comment.depth, "like_count": 0, "reply_count": 0,
            "is_deleted": False, "created_at": comment.created_at.isoformat(),
            "updated_at": comment.updated_at.isoformat(),
        },
    })
    # Notify feed so homepage comment counts stay in sync
    await publish("threads:feed", {
        "type": "new_comment",
        "data": {"thread_id": str(thread_id)},
    })

    return comment


async def update_comment(db, comment_id: uuid.UUID, data, user: UserContext) -> Comment:
    comment = await get_comment_by_id(db, comment_id)
    if comment.is_deleted:
        raise NotFoundError("Comment not found")
    if comment.author_id != user.id:
        raise ForbiddenError("You can only edit your own comments")

    comment.content = _sanitize(data.content)
    comment.edited_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(comment)

    # Broadcast edit to thread room
    await publish(f"thread:{comment.thread_id}", {
        "type": "comment_edited",
        "data": {
            "id": str(comment.id),
            "content": comment.content,
            "edited_at": comment.edited_at.isoformat(),
        },
    })

    return comment


async def delete_comment(db, comment_id: uuid.UUID, user: UserContext) -> None:
    comment = await get_comment_by_id(db, comment_id)
    if comment.is_deleted:
        raise NotFoundError("Comment not found")
    if comment.author_id != user.id:
        if user.role == "member":
            raise ForbiddenError("You can only delete your own comments")
        if not _can_moderate(user.role, comment.author_role):
            raise ForbiddenError("Cannot moderate content from users at your role level or above")

    comment.is_deleted = True
    await db.execute(
        update(Thread).where(Thread.id == comment.thread_id).values(comment_count=Thread.comment_count - 1)
    )

    if comment.author_id != user.id:
        await _publish_audit_event(user.id, "delete_comment", "comment", comment.id, {})

    await db.flush()

    # Broadcast deletion to thread room
    await publish(f"thread:{comment.thread_id}", {
        "type": "comment_deleted",
        "data": {
            "comment_id": str(comment.id),
            "author_username": comment.author_username,
            "author_id": str(comment.author_id),
        },
    })
    # Notify feed so homepage comment counts stay in sync
    await publish("threads:feed", {
        "type": "comment_deleted",
        "data": {"thread_id": str(comment.thread_id)},
    })


def mask_deleted_comment(comment: Comment) -> dict:
    """Return comment dict with content masked if deleted or author deactivated."""
    if comment.is_deleted or not comment.author_is_active:
        return {
            "id": comment.id, "content": "[deleted]" if comment.is_deleted else "[account deactivated]",
            "thread_id": comment.thread_id,
            "author_id": comment.author_id,
            "author_username": comment.author_username if comment.is_deleted else "",
            "parent_id": comment.parent_id,
            "depth": comment.depth, "like_count": comment.like_count,
            "reply_count": comment.reply_count, "is_deleted": comment.is_deleted,
            "is_edited": comment.is_edited, "edited_at": comment.edited_at,
            "created_at": comment.created_at, "updated_at": comment.updated_at,
        }
    return {
        "id": comment.id, "content": comment.content, "thread_id": comment.thread_id,
        "author_id": comment.author_id, "author_username": comment.author_username,
        "parent_id": comment.parent_id, "depth": comment.depth,
        "like_count": comment.like_count, "reply_count": comment.reply_count,
        "is_deleted": False, "is_edited": comment.is_edited, "edited_at": comment.edited_at,
        "created_at": comment.created_at, "updated_at": comment.updated_at,
    }
