"""Comment routes — CRUD, like, report for comments."""

import uuid

from fastapi import APIRouter, Query

from shared.schemas import CursorPage, MessageResponse
from app.core.deps import AuthUser, DbSession
from app.schemas import (
    CommentCreate, CommentRead, CommentUpdate,
    LikeResponse, LikerRead, ReportCreate, ReportRead,
)
from app import services

comments_router = APIRouter(tags=["Comments"])


@comments_router.get("/threads/{thread_id}/comments", response_model=CursorPage[CommentRead])
async def list_comments(
    thread_id: uuid.UUID, db: DbSession,
    sort: str = Query("new", regex="^(new|old|top)$"),
    cursor: str | None = Query(None), limit: int = Query(50, ge=1, le=100),
) -> CursorPage[CommentRead]:
    comments, next_cursor = await services.list_comments(db, thread_id, sort=sort, cursor=cursor, limit=limit)
    return CursorPage(
        items=[CommentRead(**services.mask_deleted_comment(c)) for c in comments],
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


@comments_router.post("/threads/{thread_id}/comments", response_model=CommentRead, status_code=201)
async def create_comment(thread_id: uuid.UUID, data: CommentCreate, db: DbSession, user: AuthUser) -> CommentRead:
    comment = await services.create_comment(db, thread_id, data, user)
    return CommentRead.model_validate(comment)


@comments_router.get("/comments/{comment_id}/replies", response_model=CursorPage[CommentRead])
async def list_replies(
    comment_id: uuid.UUID, db: DbSession,
    cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=100),
) -> CursorPage[CommentRead]:
    replies, next_cursor = await services.list_replies(db, comment_id, cursor=cursor, limit=limit)
    return CursorPage(
        items=[CommentRead(**services.mask_deleted_comment(r)) for r in replies],
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


@comments_router.patch("/comments/{comment_id}", response_model=CommentRead)
async def update_comment(comment_id: uuid.UUID, data: CommentUpdate, db: DbSession, user: AuthUser) -> CommentRead:
    comment = await services.update_comment(db, comment_id, data, user)
    return CommentRead.model_validate(comment)


@comments_router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(comment_id: uuid.UUID, db: DbSession, user: AuthUser) -> MessageResponse:
    await services.delete_comment(db, comment_id, user)
    return MessageResponse(message="Comment deleted")


@comments_router.post("/comments/{comment_id}/like", response_model=LikeResponse)
async def toggle_comment_like(comment_id: uuid.UUID, db: DbSession, user: AuthUser) -> LikeResponse:
    liked, count = await services.toggle_comment_like(db, comment_id, user)
    return LikeResponse(liked=liked, like_count=count)


@comments_router.get("/comments/{comment_id}/like/status", response_model=LikeResponse)
async def comment_like_status(comment_id: uuid.UUID, db: DbSession, user: AuthUser) -> LikeResponse:
    comment = await services.get_comment_by_id(db, comment_id)
    liked = await services.has_user_liked_comment(db, comment_id, user.id)
    return LikeResponse(liked=liked, like_count=comment.like_count)


@comments_router.get("/comments/{comment_id}/likers", response_model=CursorPage[LikerRead])
async def list_comment_likers(
    comment_id: uuid.UUID, db: DbSession,
    cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=100),
) -> CursorPage[LikerRead]:
    await services.get_comment_by_id(db, comment_id)
    likes, next_cursor = await services.list_comment_likers(db, comment_id, cursor=cursor, limit=limit)
    return CursorPage(
        items=[LikerRead(id=l.user_id, username="", avatar_url=None) for l in likes],
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


@comments_router.post("/comments/{comment_id}/report", response_model=ReportRead, status_code=201)
async def report_comment(comment_id: uuid.UUID, data: ReportCreate, db: DbSession, user: AuthUser) -> ReportRead:
    await services.get_comment_by_id(db, comment_id)
    report = await services.create_report(db, reporter_id=user.id, target_type="comment", target_id=comment_id, reason=data.reason.value, description=data.description)
    return ReportRead.model_validate(report)
