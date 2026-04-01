"""Report schemas."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from pydantic import BaseModel, ConfigDict, Field


class ReportReason(str, PyEnum):
    SPAM = "spam"
    HARASSMENT = "harassment"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class ReportCreate(BaseModel):
    reason: ReportReason
    description: str | None = Field(None, max_length=1000)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reporter_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    thread_id: uuid.UUID | None = None
    target_content: str | None = None
    target_author_username: str | None = None
    reason: str
    description: str | None
    status: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime


class ReportResolve(BaseModel):
    action: str = Field(pattern=r"^(resolved|dismissed)$")
