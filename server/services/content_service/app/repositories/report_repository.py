"""Report repository — all report-related data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment, Report, Thread
from app.services.helpers import _parse_cursor_dt


class ReportRepository:
    """Encapsulates all database operations for the Report model."""

    @staticmethod
    async def find_by_id(db: AsyncSession, report_id: uuid.UUID) -> Report | None:
        result = await db.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def find_pending_duplicate(db: AsyncSession, reporter_id: uuid.UUID, target_type: str, target_id: uuid.UUID) -> Report | None:
        result = await db.execute(
            select(Report).where(
                Report.reporter_id == reporter_id,
                Report.target_type == target_type,
                Report.target_id == target_id,
                Report.status == "pending",
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_target_author(db: AsyncSession, target_type: str, target_id: uuid.UUID) -> uuid.UUID | None:
        if target_type == "thread":
            target = (await db.execute(select(Thread).where(Thread.id == target_id))).scalar_one_or_none()
            return target.author_id if target else None
        elif target_type == "comment":
            target = (await db.execute(select(Comment).where(Comment.id == target_id))).scalar_one_or_none()
            return target.author_id if target else None
        return None

    @staticmethod
    async def create(db: AsyncSession, report: Report) -> Report:
        db.add(report)
        await db.flush()
        return report

    @staticmethod
    async def list_paginated(db: AsyncSession, *, status: str | None = None, cursor: str | None = None, limit: int = 20):
        stmt = select(Report).order_by(Report.created_at.desc())
        if status:
            stmt = stmt.where(Report.status == status)
        if cursor:
            stmt = stmt.where(Report.created_at < _parse_cursor_dt(cursor))
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        reports = list(result.scalars().all())

        next_cursor = None
        if len(reports) > limit:
            reports = reports[:limit]
            next_cursor = reports[-1].created_at.isoformat()

        return reports, next_cursor

    @staticmethod
    async def count_pending(db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(Report.id)).where(Report.status == "pending")
        )
        return result.scalar_one()

    @staticmethod
    async def batch_comment_meta(db: AsyncSession, comment_ids: list[uuid.UUID]) -> dict:
        if not comment_ids:
            return {}
        result = await db.execute(
            select(Comment.id, Comment.thread_id, Comment.content, Comment.author_username)
            .where(Comment.id.in_(comment_ids))
        )
        return {row.id: (row.thread_id, row.content, row.author_username) for row in result.all()}

    @staticmethod
    async def batch_thread_meta(db: AsyncSession, thread_ids: list[uuid.UUID]) -> dict:
        if not thread_ids:
            return {}
        result = await db.execute(
            select(Thread.id, Thread.title, Thread.author_username)
            .where(Thread.id.in_(thread_ids))
        )
        return {row.id: (row.title, row.author_username) for row in result.all()}
