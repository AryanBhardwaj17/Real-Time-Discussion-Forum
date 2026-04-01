"""Comment model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "comments"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    author_username: Mapped[str] = mapped_column(String(50), nullable=False, server_default="")
    author_role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    depth: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    like_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    author_is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    thread: Mapped["Thread"] = relationship(back_populates="comments", lazy="noload")
    parent: Mapped["Comment | None"] = relationship(remote_side="Comment.id", lazy="noload")
    likes: Mapped[list["CommentLike"]] = relationship(back_populates="comment", cascade="all, delete-orphan", lazy="noload")

    @hybrid_property
    def is_edited(self) -> bool:
        return self.edited_at is not None

    @is_edited.inplace.expression
    @classmethod
    def _is_edited_expr(cls):
        return cls.edited_at.isnot(None)

    __table_args__ = (
        Index("ix_comments_active_thread", "thread_id", "created_at", postgresql_where=(is_deleted.is_(False))),
    )
