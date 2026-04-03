"""Dashboard service schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PlatformStats(BaseModel):
    total_users: int
    active_users: int
    total_threads: int
    total_comments: int
    pending_reports: int


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    target_type: str
    target_id: uuid.UUID
    details: dict | None
    created_at: datetime


class PersonalStats(BaseModel):
    thread_count: int
    comment_count: int
    likes_received: int
