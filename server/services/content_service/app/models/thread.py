"""Thread model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tag import Tag, thread_tags_table


class Thread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "threads"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    author_username: Mapped[str] = mapped_column(String(50), nullable=False, server_default="")
    author_role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member")

    like_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    hot_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)

    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    author_is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tag_objects: Mapped[list["Tag"]] = relationship(secondary=thread_tags_table, lazy="selectin")
    comments: Mapped[list["Comment"]] = relationship(back_populates="thread", cascade="all, delete-orphan", lazy="noload")
    likes: Mapped[list["ThreadLike"]] = relationship(back_populates="thread", cascade="all, delete-orphan", lazy="noload")

    # Computed properties (replace redundant boolean columns)
    @hybrid_property
    def is_pinned(self) -> bool:
        return self.pinned_at is not None

    @is_pinned.inplace.expression
    @classmethod
    def _is_pinned_expr(cls):
        return cls.pinned_at.isnot(None)

    @hybrid_property
    def is_locked(self) -> bool:
        return self.locked_at is not None

    @is_locked.inplace.expression
    @classmethod
    def _is_locked_expr(cls):
        return cls.locked_at.isnot(None)

    @hybrid_property
    def is_edited(self) -> bool:
        return self.edited_at is not None

    @is_edited.inplace.expression
    @classmethod
    def _is_edited_expr(cls):
        return cls.edited_at.isnot(None)

    @property
    def tags(self) -> list[str]:
        return [t.name for t in self.tag_objects] if self.tag_objects else []

    __table_args__ = (
        Index("ix_threads_active_created", "created_at", postgresql_where=(is_deleted.is_(False))),
        Index("ix_threads_active_hot", "hot_score", postgresql_where=(is_deleted.is_(False))),
    )
