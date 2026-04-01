"""Like schemas."""

import uuid

from pydantic import BaseModel, ConfigDict


class LikeResponse(BaseModel):
    liked: bool
    like_count: int


class LikerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    avatar_url: str | None = None
