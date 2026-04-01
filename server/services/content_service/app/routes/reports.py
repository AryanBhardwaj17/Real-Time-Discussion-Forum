"""Report management routes — admin/moderator endpoints."""

import uuid

from fastapi import APIRouter, Query

from shared.schemas import CursorPage
from app.core.deps import DbSession, ModUser
from app.schemas import ReportRead, ReportResolve
from app import services

reports_router = APIRouter(prefix="/reports", tags=["Reports"])


@reports_router.get("", response_model=CursorPage[ReportRead])
async def list_reports(
    db: DbSession, mod: ModUser,
    status: str | None = Query(None, regex="^(pending|resolved|dismissed)$"),
    cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=100),
) -> CursorPage[ReportRead]:
    reports, next_cursor = await services.list_reports(db, status=status, cursor=cursor, limit=limit)
    items = await services.enrich_reports_with_thread_id(db, reports)
    return CursorPage(
        items=items,
        next_cursor=next_cursor, has_more=next_cursor is not None,
    )


@reports_router.post("/{report_id}/resolve", response_model=ReportRead)
async def resolve_report(report_id: uuid.UUID, data: ReportResolve, db: DbSession, mod: ModUser) -> ReportRead:
    report = await services.resolve_report(db, report_id, mod, data.action)
    items = await services.enrich_reports_with_thread_id(db, [report])
    return items[0]
