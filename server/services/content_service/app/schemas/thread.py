"""Thread schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThreadCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=1, max_length=20000)
    tags: list[str] | None = Field(None, max_length=10)

    @field_validator("tags", mode="before")
    @classmethod
    def _validate_tag_strings(cls, v):
        if v is not None:
            for tag in v:
                if not isinstance(tag, str) or len(tag) < 1 or len(tag) > 50:
                    raise ValueError("Each tag must be 1-50 characters")
        return v


class ThreadUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=300)
    description: str | None = Field(None, min_length=1, max_length=20000)
    tags: list[str] | None = None


class ThreadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    author_id: uuid.UUID
    author_username: str
    tags: list[str] | None
    like_count: int
    comment_count: int
    hot_score: float
    is_pinned: bool
    is_locked: bool
    is_deleted: bool
    is_edited: bool = False
    edited_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ThreadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    author_id: uuid.UUID
    author_username: str
    tags: list[str] | None
    like_count: int
    comment_count: int
    hot_score: float
    is_pinned: bool
    is_locked: bool
    is_edited: bool = False
    edited_at: datetime | None = None
    created_at: datetime
