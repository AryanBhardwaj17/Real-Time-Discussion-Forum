"""Search service schemas — thread search results from Meilisearch."""

from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


class ThreadSearchResult(BaseModel):
    """Thread data returned directly from Meilisearch (no DB hydration needed)."""

    id: str
    title: str
    description: str
    author_id: str
    author_username: str
    tags: list[str] | None = None
    like_count: int = 0
    comment_count: int = 0
    hot_score: float = 0.0
    is_pinned: bool = False
    is_locked: bool = False
    created_at: str | float | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_created_at(cls, v):
        """Convert epoch-seconds float to ISO-8601 string for the frontend."""
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
        return v
