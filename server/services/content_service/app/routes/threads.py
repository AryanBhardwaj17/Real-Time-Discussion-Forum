"""Thread routes — CRUD, like, report, pin, lock."""

import uuid

from fastapi import APIRouter, Query

from shared.schemas import CursorPage, MessageResponse
from app.core.deps import AuthUser, DbSession, ModUser
from app.schemas import (
    LikeResponse, LikerRead, ReportCreate, ReportRead,
    ThreadCreate, ThreadListItem, ThreadRead, ThreadUpdate,
)
from app import services

threads_router = APIRouter(prefix="/threads", tags=["Threads"])


@threads_router.get("", response_model=CursorPage[ThreadListItem])
async def list_threads(
    db: DbSession,
    sort: str = Query("hot", regex="^(hot|new|top)$"),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> CursorPage[ThreadListItem]:
    threads, next_cursor = await services.list_threads(db, sort=sort, cursor=cursor, limit=limit)
    return CursorPage(
        items=[ThreadListItem.model_validate(t) for t in threads],
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


@threads_router.post("", response_model=ThreadRead, status_code=201)
async def create_thread(data: ThreadCreate, db: DbSession, user: AuthUser) -> ThreadRead:
    thread = await services.create_thread(db, data, user)
    return ThreadRead.model_validate(thread)


@threads_router.get("/{thread_id}", response_model=ThreadRead)
async def get_thread(thread_id: uuid.UUID, db: DbSession) -> ThreadRead:
    thread = await services.get_thread_by_id(db, thread_id)
    return ThreadRead.model_validate(thread)


@threads_router.patch("/{thread_id}", response_model=ThreadRead)
async def update_thread(thread_id: uuid.UUID, data: ThreadUpdate, db: DbSession, user: AuthUser) -> ThreadRead:
    thread = await services.update_thread(db, thread_id, data, user)
    return ThreadRead.model_validate(thread)


@threads_router.delete("/{thread_id}", response_model=MessageResponse)
async def delete_thread(thread_id: uuid.UUID, db: DbSession, user: AuthUser) -> MessageResponse:
    await services.delete_thread(db, thread_id, user)
    return MessageResponse(message="Thread deleted")


@threads_router.post("/{thread_id}/like", response_model=LikeResponse)
async def toggle_like(thread_id: uuid.UUID, db: DbSession, user: AuthUser) -> LikeResponse:
    liked, count = await services.toggle_thread_like(db, thread_id, user)
    return LikeResponse(liked=liked, like_count=count)


@threads_router.get("/{thread_id}/like/status", response_model=LikeResponse)
async def like_status(thread_id: uuid.UUID, db: DbSession, user: AuthUser) -> LikeResponse:
    thread = await services.get_thread_by_id(db, thread_id)
    liked = await services.has_user_liked_thread(db, thread_id, user.id)
    return LikeResponse(liked=liked, like_count=thread.like_count)


@threads_router.get("/{thread_id}/likers", response_model=CursorPage[LikerRead])
async def list_likers(
    thread_id: uuid.UUID, db: DbSession,
    cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=100),
) -> CursorPage[LikerRead]:
    await services.get_thread_by_id(db, thread_id)
    likes, next_cursor = await services.list_thread_likers(db, thread_id, cursor=cursor, limit=limit)
    return CursorPage(
        items=[LikerRead(id=l.user_id, username="", avatar_url=None) for l in likes],
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


@threads_router.post("/{thread_id}/report", response_model=ReportRead, status_code=201)
async def report_thread(thread_id: uuid.UUID, data: ReportCreate, db: DbSession, user: AuthUser) -> ReportRead:
    await services.get_thread_by_id(db, thread_id)
    report = await services.create_report(db, reporter_id=user.id, target_type="thread", target_id=thread_id, reason=data.reason.value, description=data.description)
    return ReportRead.model_validate(report)


@threads_router.post("/{thread_id}/pin", response_model=ThreadRead)
async def toggle_pin(thread_id: uuid.UUID, db: DbSession, mod: ModUser) -> ThreadRead:
    thread = await services.toggle_pin(db, thread_id, mod)
    return ThreadRead.model_validate(thread)


@threads_router.post("/{thread_id}/lock", response_model=ThreadRead)
async def toggle_lock(thread_id: uuid.UUID, db: DbSession, mod: ModUser) -> ThreadRead:
    thread = await services.toggle_lock(db, thread_id, mod)
    return ThreadRead.model_validate(thread)
