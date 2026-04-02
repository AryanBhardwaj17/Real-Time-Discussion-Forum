"""Notification service models."""

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationType(str, enum.Enum):
    """Python-side validation only. DB column is VARCHAR with FK to notification_types lookup table."""
    REPLY = "reply"
    MENTION = "mention"
    THREAD_LIKE = "thread_like"
    COMMENT_LIKE = "comment_like"


class ReferenceType(str, enum.Enum):
    """Python-side documentation. DB column is bare VARCHAR (set by code, not user input)."""
    THREAD = "thread"
    COMMENT = "comment"


# ── Lookup Table ─────────────────────────────────────────────────────

class NotificationTypeLookup(Base):
    __tablename__ = "notification_types"

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(
        String(30), ForeignKey("notification_types.code"), nullable=False,
    )
    reference_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read", "created_at"),
        UniqueConstraint(
            "user_id", "actor_id", "type", "reference_id",
            name="uq_notification_idempotency",
        ),
    )
