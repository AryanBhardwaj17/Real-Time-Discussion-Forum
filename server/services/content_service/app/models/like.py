"""Like models — ThreadLike and CommentLike."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ThreadLike(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "thread_likes"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    thread: Mapped["Thread"] = relationship(back_populates="likes", lazy="noload")

    __table_args__ = (UniqueConstraint("user_id", "thread_id", name="uq_thread_like_user_thread"),)


class CommentLike(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "comment_likes"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    comment: Mapped["Comment"] = relationship(back_populates="likes", lazy="noload")

    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="uq_comment_like_user_comment"),)
