"""Internal API routes — for Dashboard service, not exposed through gateway."""

import uuid

from fastapi import APIRouter, Depends, Query, Request

from shared.exceptions import ForbiddenError
from app.core.config import get_settings
from app.core.deps import DbSession
from app.schemas import CommentRead, ThreadListItem
from app import services

internal_router = APIRouter(prefix="/internal", tags=["Internal"])


async def _verify_internal_secret(request: Request) -> None:
    """Verify the caller provides the shared internal secret."""
    settings = get_settings()
    if not settings.INTERNAL_SECRET:
        raise ForbiddenError("Internal secret not configured")
    provided = request.headers.get("X-Internal-Secret", "")
    if provided != settings.INTERNAL_SECRET:
        raise ForbiddenError("Invalid internal secret")


@internal_router.get("/stats", dependencies=[Depends(_verify_internal_secret)])
async def content_stats(db: DbSession) -> dict:
    return await services.get_content_stats(db)


@internal_router.get("/users/{user_id}/threads", dependencies=[Depends(_verify_internal_secret)])
async def user_threads(user_id: uuid.UUID, db: DbSession, cursor: str | None = Query(None), limit: int = Query(20)):
    threads, next_cursor = await services.get_user_threads(db, user_id, cursor=cursor, limit=limit)
    return {"items": [ThreadListItem.model_validate(t) for t in threads], "next_cursor": next_cursor, "has_more": next_cursor is not None}


@internal_router.get("/users/{user_id}/comments", dependencies=[Depends(_verify_internal_secret)])
async def user_comments(user_id: uuid.UUID, db: DbSession, cursor: str | None = Query(None), limit: int = Query(20)):
    comments, next_cursor = await services.get_user_comments(db, user_id, cursor=cursor, limit=limit)
    return {"items": [CommentRead(**services.mask_deleted_comment(c)) for c in comments], "next_cursor": next_cursor, "has_more": next_cursor is not None}


@internal_router.get("/users/{user_id}/stats", dependencies=[Depends(_verify_internal_secret)])
async def user_content_stats(user_id: uuid.UUID, db: DbSession) -> dict:
    return await services.get_user_content_stats(db, user_id)


@internal_router.get("/activity", dependencies=[Depends(_verify_internal_secret)])
async def recent_activity(db: DbSession, hours: int = Query(24, ge=1, le=168), limit: int = Query(20, ge=1, le=100)) -> dict:
    return await services.get_recent_activity(db, hours=hours, limit=limit)


@internal_router.post("/reindex", dependencies=[Depends(_verify_internal_secret)])
async def reindex_meilisearch(db: DbSession) -> dict:
    """Re-index all non-deleted threads into Meilisearch."""
    count = await services.reindex_all_threads(db)
    return {"reindexed": count}
