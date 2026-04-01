"""Thread service — CRUD, pin, lock, hot score."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ForbiddenError, NotFoundError
from shared.logging import get_logger

from app.core.deps import UserContext
from app.models import Comment, Tag, Thread, ThreadLike, thread_tags_table
from app.core.redis import publish
from app.repositories import ThreadRepository, TagRepository
from app.services.helpers import (
    _can_moderate,
    _compute_hot_score,
    _meili_delete_thread,
    _meili_index_thread,
    _meili_update_thread,
    _publish_audit_event,
    _sanitize,
    _thread_to_meili_doc,
)

logger = get_logger(__name__)


async def get_thread_by_id(db: AsyncSession, thread_id: uuid.UUID) -> Thread:
    thread = await ThreadRepository.find_by_id(db, thread_id)
    if thread is None:
        raise NotFoundError("Thread not found")
    return thread


async def list_threads(db: AsyncSession, *, sort: str = "hot", cursor: str | None = None, limit: int = 20):
    return await ThreadRepository.list_paginated(db, sort=sort, cursor=cursor, limit=limit)


async def create_thread(db: AsyncSession, data, user: UserContext) -> Thread:
    thread = Thread(
        title=_sanitize(data.title),
        description=_sanitize(data.description),
        author_id=user.id,
        author_username=user.username,
        author_role=user.role,
        hot_score=_compute_hot_score(0, datetime.now(timezone.utc)),
    )
    await ThreadRepository.create(db, thread)

    if data.tags:
        tags = await TagRepository.get_or_create_many(db, data.tags)
        for tag in tags:
            await db.execute(thread_tags_table.insert().values(thread_id=thread.id, tag_id=tag.id))
            await TagRepository.increment_usage(db, tag.id)
        await db.flush()

    # Refresh to load tag_objects via selectin for response serialisation
    await db.refresh(thread, attribute_names=["tag_objects"])

    await publish("threads:feed", {
        "type": "new_thread",
        "data": {
            "id": str(thread.id),
            "title": thread.title,
            "description": thread.description,
            "author_id": str(thread.author_id),
            "author_username": user.username,
            "tags": [t.name for t in thread.tag_objects] if thread.tag_objects else [],
            "like_count": 0,
            "comment_count": 0,
            "hot_score": thread.hot_score,
            "is_pinned": False,
            "is_locked": False,
            "is_edited": False,
            "edited_at": None,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
        },
    })

    await _meili_index_thread(_thread_to_meili_doc(thread))
    logger.info("thread_created", thread_id=str(thread.id))
    return thread


async def update_thread(db: AsyncSession, thread_id: uuid.UUID, data, user: UserContext) -> Thread:
    thread = await get_thread_by_id(db, thread_id)

    if thread.author_id != user.id:
        raise ForbiddenError("You can only edit your own threads")

    update_data = data.model_dump(exclude_unset=True)

    # Handle tags separately via junction table
    new_tag_names = update_data.pop("tags", None)
    if new_tag_names is not None:
        old_tags = list(thread.tag_objects)
        new_tags = await TagRepository.get_or_create_many(db, new_tag_names)
        for tag in old_tags:
            await TagRepository.decrement_usage(db, tag.id)
        # Clear old associations and insert new ones (avoid sync lazy load)
        await ThreadRepository.set_tag_associations(db, thread.id, [t.id for t in new_tags])
        for tag in new_tags:
            await TagRepository.increment_usage(db, tag.id)

    for field, value in update_data.items():
        if isinstance(value, str):
            value = _sanitize(value)
        setattr(thread, field, value)

    thread.edited_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(thread)
    tags = thread.tags  # tags property uses selectin-loaded tag_objects

    thread_event = {
        "type": "thread_updated",
        "data": {
            "id": str(thread.id),
            "title": thread.title,
            "description": thread.description,
            "tags": tags,
            "is_edited": True,
            "edited_at": thread.edited_at.isoformat(),
        },
    }
    await publish(f"thread:{thread.id}", thread_event)
    await publish("threads:feed", thread_event)

    await _meili_index_thread(_thread_to_meili_doc(thread))
    return thread


async def delete_thread(db: AsyncSession, thread_id: uuid.UUID, user: UserContext) -> None:
    thread = await get_thread_by_id(db, thread_id)

    if thread.author_id != user.id:
        if user.role == "member":
            raise ForbiddenError("You can only delete your own threads")
        if not _can_moderate(user.role, thread.author_role):
            raise ForbiddenError("Cannot moderate content from users at your role level or above")

    thread.is_deleted = True

    if thread.author_id != user.id:
        await _publish_audit_event(user.id, "delete_thread", "thread", thread.id, {})

    await db.flush()

    delete_event = {
        "type": "thread_deleted",
        "data": {"id": str(thread.id)},
    }
    await publish(f"thread:{thread.id}", delete_event)
    await publish("threads:feed", delete_event)

    await _meili_delete_thread(str(thread.id))


async def toggle_pin(db: AsyncSession, thread_id: uuid.UUID, actor: UserContext) -> Thread:
    thread = await get_thread_by_id(db, thread_id)
    if thread.author_id != actor.id and not _can_moderate(actor.role, thread.author_role):
        raise ForbiddenError("Cannot pin/unpin threads from users at your role level or above")
    if thread.pinned_at is not None:
        thread.pinned_at = None
    else:
        thread.pinned_at = datetime.now(timezone.utc)
    await _publish_audit_event(actor.id, "pin_thread", "thread", thread.id, {"pinned": thread.is_pinned})
    await db.flush()
    await db.refresh(thread)

    pin_event = {
        "type": "thread_pinned",
        "data": {"id": str(thread.id), "is_pinned": thread.is_pinned},
    }
    await publish(f"thread:{thread.id}", pin_event)
    await publish("threads:feed", pin_event)

    return thread


async def toggle_lock(db: AsyncSession, thread_id: uuid.UUID, actor: UserContext) -> Thread:
    thread = await get_thread_by_id(db, thread_id)
    if thread.author_id != actor.id and not _can_moderate(actor.role, thread.author_role):
        raise ForbiddenError("Cannot lock/unlock threads from users at your role level or above")
    if thread.locked_at is not None:
        thread.locked_at = None
        thread.locked_by = None
    else:
        thread.locked_at = datetime.now(timezone.utc)
        thread.locked_by = actor.id
    await _publish_audit_event(actor.id, "lock_thread", "thread", thread.id, {"locked": thread.is_locked})
    await db.flush()
    await db.refresh(thread)

    lock_event = {
        "type": "thread_locked",
        "data": {"id": str(thread.id), "is_locked": thread.is_locked},
    }
    await publish(f"thread:{thread.id}", lock_event)
    await publish("threads:feed", lock_event)

    return thread


async def recalculate_hot_score(db: AsyncSession, thread: Thread) -> None:
    thread.hot_score = _compute_hot_score(thread.like_count, thread.created_at)
    await db.flush()
    await _meili_update_thread({"id": str(thread.id), "like_count": thread.like_count, "hot_score": thread.hot_score})
