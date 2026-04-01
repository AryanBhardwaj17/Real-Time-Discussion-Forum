"""Public profile routes — exposed through gateway, no auth required."""

import uuid

from fastapi import APIRouter, Query

from app.core.deps import DbSession
from app.schemas import ThreadListItem
from app import services

profile_router = APIRouter(prefix="/profiles", tags=["Profiles"])


@profile_router.get("/{user_id}/threads")
async def public_user_threads(
    user_id: uuid.UUID, db: DbSession,
    cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=100),
) -> dict:
    threads, next_cursor = await services.get_user_threads(db, user_id, cursor=cursor, limit=limit)
    return {"items": [ThreadListItem.model_validate(t) for t in threads], "next_cursor": next_cursor, "has_more": next_cursor is not None}


@profile_router.get("/{user_id}/stats")
async def public_user_stats(user_id: uuid.UUID, db: DbSession) -> dict:
    return await services.get_user_content_stats(db, user_id)
