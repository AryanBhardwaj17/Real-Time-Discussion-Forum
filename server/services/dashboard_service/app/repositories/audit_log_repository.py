"""AuditLog repository — audit log data access."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ValidationError
from app.models import AuditLog


class AuditLogRepository:
    """Encapsulates all database operations for the AuditLog model."""

    @staticmethod
    async def list_paginated(db: AsyncSession, *, cursor: str | None = None, limit: int = 30):
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if cursor:
            parts = cursor.split("|", 1)
            if len(parts) == 2:
                try:
                    cursor_dt = datetime.fromisoformat(parts[0])
                    cursor_id = uuid.UUID(parts[1])
                except (ValueError, TypeError):
                    raise ValidationError("Invalid cursor format")
                stmt = stmt.where(
                    (AuditLog.created_at < cursor_dt)
                    | ((AuditLog.created_at == cursor_dt) & (AuditLog.id < cursor_id))
                )
            else:
                try:
                    cursor_dt = datetime.fromisoformat(cursor)
                except (ValueError, TypeError):
                    raise ValidationError("Invalid cursor format")
                stmt = stmt.where(AuditLog.created_at < cursor_dt)
        stmt = stmt.limit(limit + 1)

        result = await db.execute(stmt)
        logs = list(result.scalars().all())

        next_cursor = None
        if len(logs) > limit:
            logs = logs[:limit]
            next_cursor = f"{logs[-1].created_at.isoformat()}|{logs[-1].id}"

        return logs, next_cursor
