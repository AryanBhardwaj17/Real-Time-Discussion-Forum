"""Dashboard service routes — aggregated views using inter-service calls."""

import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ForbiddenError, UnauthorizedError
from shared.schemas import CursorPage, MessageResponse
from app.core.config import get_settings
from app.db import get_db
from app.repositories import AuditLogRepository
from app.schemas import AuditLogRead, PlatformStats, PersonalStats

settings = get_settings()
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _internal_headers() -> dict[str, str]:
    """Headers to include on inter-service internal API calls."""
    h: dict[str, str] = {}
    if settings.INTERNAL_SECRET:
        h["X-Internal-Secret"] = settings.INTERNAL_SECRET
    return h


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_user_id(request: Request) -> uuid.UUID:
    uid = request.headers.get("X-User-ID")
    if not uid:
        raise UnauthorizedError("Authentication required")
    return uuid.UUID(uid)


async def _require_admin(request: Request) -> uuid.UUID:
    uid = request.headers.get("X-User-ID")
    role = request.headers.get("X-User-Role", "member")
    if not uid:
        raise UnauthorizedError("Authentication required")
    if role != "admin":
        raise ForbiddenError("Admin access required")
    return uuid.UUID(uid)


async def _require_mod(request: Request) -> uuid.UUID:
    uid = request.headers.get("X-User-ID")
    role = request.headers.get("X-User-Role", "member")
    if not uid:
        raise UnauthorizedError("Authentication required")
    if role not in ("admin", "moderator"):
        raise ForbiddenError("Moderator access required")
    return uuid.UUID(uid)


UserId = Annotated[uuid.UUID, Depends(_get_user_id)]
AdminId = Annotated[uuid.UUID, Depends(_require_admin)]
ModId = Annotated[uuid.UUID, Depends(_require_mod)]


# ── Admin Endpoints ──────────────────────────────────────────────────

@router.get("/admin/stats", response_model=PlatformStats)
async def platform_stats(admin: AdminId) -> PlatformStats:
    """Aggregate stats from Auth + Content services."""
    auth_data, content_data = {}, {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            auth_resp = await client.get(f"{settings.AUTH_SERVICE_URL}/internal/stats", headers=_internal_headers())
            auth_data = auth_resp.json() if auth_resp.status_code == 200 else {}
        except httpx.HTTPError:
            pass

        try:
            content_resp = await client.get(f"{settings.CONTENT_SERVICE_URL}/internal/stats", headers=_internal_headers())
            content_data = content_resp.json() if content_resp.status_code == 200 else {}
        except httpx.HTTPError:
            pass

    return PlatformStats(
        total_users=auth_data.get("total_users", 0),
        active_users=auth_data.get("active_users", 0),
        total_threads=content_data.get("total_threads", 0),
        total_comments=content_data.get("total_comments", 0),
        pending_reports=content_data.get("pending_reports", 0),
    )


@router.get("/admin/audit-log", response_model=CursorPage[AuditLogRead])
async def audit_log(
    db: DbSession, admin: AdminId,
    cursor: str | None = Query(None), limit: int = Query(30, ge=1, le=100),
) -> CursorPage[AuditLogRead]:
    logs, next_cursor = await AuditLogRepository.list_paginated(db, cursor=cursor, limit=limit)
    return CursorPage(
        items=[AuditLogRead.model_validate(log) for log in logs],
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


# ── Moderator Endpoints ─────────────────────────────────────────────

@router.get("/mod/activity")
async def recent_activity(
    mod: ModId,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Fetch recent activity from Content service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.CONTENT_SERVICE_URL}/internal/activity",
                params={"hours": hours, "limit": limit},
                headers=_internal_headers(),
            )
            return resp.json() if resp.status_code == 200 else {"recent_threads": [], "recent_comments": []}
    except httpx.HTTPError:
        return {"recent_threads": [], "recent_comments": []}


# ── Member Endpoints ─────────────────────────────────────────────────

@router.get("/me/threads")
async def my_threads(
    user_id: UserId,
    cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=100),
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.CONTENT_SERVICE_URL}/internal/users/{user_id}/threads",
                params={"cursor": cursor, "limit": limit} if cursor else {"limit": limit},
                headers=_internal_headers(),
            )
            return resp.json() if resp.status_code == 200 else {"items": [], "next_cursor": None, "has_more": False}
    except httpx.HTTPError:
        return {"items": [], "next_cursor": None, "has_more": False}


@router.get("/me/comments")
async def my_comments(
    user_id: UserId,
    cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=100),
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.CONTENT_SERVICE_URL}/internal/users/{user_id}/comments",
                params={"cursor": cursor, "limit": limit} if cursor else {"limit": limit},
                headers=_internal_headers(),
            )
            return resp.json() if resp.status_code == 200 else {"items": [], "next_cursor": None, "has_more": False}
    except httpx.HTTPError:
        return {"items": [], "next_cursor": None, "has_more": False}


@router.get("/me/stats", response_model=PersonalStats)
async def my_stats(user_id: UserId) -> PersonalStats:
    data = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.CONTENT_SERVICE_URL}/internal/users/{user_id}/stats", headers=_internal_headers())
            data = resp.json() if resp.status_code == 200 else {}
    except httpx.HTTPError:
        pass
    return PersonalStats(
        thread_count=data.get("thread_count", 0),
        comment_count=data.get("comment_count", 0),
        likes_received=data.get("likes_received", 0),
    )
