"""User role enum and role lookup table."""

import enum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.base import Base


class UserRole(str, enum.Enum):
    """Python-side validation. DB column is VARCHAR with FK to lookup table."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"


class RoleLookup(Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
