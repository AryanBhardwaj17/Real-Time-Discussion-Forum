"""Report service — create, list, resolve, enrich reports."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import NotFoundError, ValidationError
from shared.logging import get_logger

from app.models import Report
from app.repositories import ReportRepository
from app.services.helpers import _publish_audit_event

logger = get_logger(__name__)


async def create_report(db: AsyncSession, *, reporter_id: uuid.UUID, target_type: str, target_id: uuid.UUID, reason: str, description: str | None = None) -> Report:
    # Prevent self-reporting
    author_id = await ReportRepository.find_target_author(db, target_type, target_id)
    if author_id and author_id == reporter_id:
        raise ValidationError("You cannot report your own content")

    # Prevent duplicate pending reports
    existing = await ReportRepository.find_pending_duplicate(db, reporter_id, target_type, target_id)
    if existing is not None:
        raise ValidationError("You have already reported this content")

    report = Report(
        reporter_id=reporter_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        description=description,
    )
    return await ReportRepository.create(db, report)


async def list_reports(db: AsyncSession, *, status: str | None = None, cursor: str | None = None, limit: int = 20):
    return await ReportRepository.list_paginated(db, status=status, cursor=cursor, limit=limit)


async def resolve_report(db: AsyncSession, report_id: uuid.UUID, user, action: str) -> Report:
    report = await ReportRepository.find_by_id(db, report_id)
    if report is None:
        raise NotFoundError("Report not found")
    if report.status != "pending":
        raise ValidationError("Report is already resolved")

    report.status = action  # "resolved" or "dismissed"
    report.reviewed_by = user.id
    report.reviewed_at = datetime.now(timezone.utc)
    await _publish_audit_event(user.id, f"report_{action}", "report", report.id, {"target_type": report.target_type, "target_id": str(report.target_id)})
    await db.flush()
    await db.refresh(report)
    return report


async def enrich_reports_with_thread_id(db: AsyncSession, reports: list[Report]) -> list:
    """Add thread_id, content preview, and author to each report for frontend navigation."""
    from app.schemas import ReportRead

    # Batch-fetch comment metadata for comment reports
    comment_ids = [r.target_id for r in reports if r.target_type == "comment"]
    comment_meta = await ReportRepository.batch_comment_meta(db, comment_ids)

    # Batch-fetch thread metadata for thread reports
    thread_ids = [r.target_id for r in reports if r.target_type == "thread"]
    thread_meta = await ReportRepository.batch_thread_meta(db, thread_ids)

    items = []
    for r in reports:
        data = ReportRead.model_validate(r)
        if r.target_type == "thread":
            data.thread_id = r.target_id
            meta = thread_meta.get(r.target_id)
            if meta:
                data.target_content = meta[0]
                data.target_author_username = meta[1]
        elif r.target_type == "comment":
            meta = comment_meta.get(r.target_id)
            if meta:
                data.thread_id = meta[0]
                data.target_content = meta[1][:200] if meta[1] else None
                data.target_author_username = meta[2]
        items.append(data)
    return items
