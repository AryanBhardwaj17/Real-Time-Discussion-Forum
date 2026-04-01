"""Comment schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    parent_id: uuid.UUID | None = None


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    thread_id: uuid.UUID
    author_id: uuid.UUID
    author_username: str
    parent_id: uuid.UUID | None
    depth: int
    like_count: int
    reply_count: int
    is_deleted: bool
    is_edited: bool = False
    edited_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
