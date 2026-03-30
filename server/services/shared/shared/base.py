"""ORM base classes shared across all database-backed microservices."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid_utils import uuid7


class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models."""

    pass


class TimestampMixin:
    """Mixin that adds ``created_at`` / ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Mixin that provides a UUID v7 primary key column.

    UUID v7 is time-ordered (monotonically increasing), which means:
    - B-tree indexes have no random page splits (much better write performance)
    - Natural chronological ordering by ID
    - Can be used as a pagination tiebreaker alongside timestamps
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: uuid.UUID(bytes=uuid7().bytes),
    )
