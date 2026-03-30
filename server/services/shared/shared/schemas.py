"""Common Pydantic schemas shared across services."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class CursorPage(BaseModel, Generic[T]):
    """Generic cursor-based pagination wrapper."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
