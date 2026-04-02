"""Notification service schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    reference_type: str
    reference_id: uuid.UUID
    actor_id: uuid.UUID
    thread_id: uuid.UUID | None = None
    content: str
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    count: int
