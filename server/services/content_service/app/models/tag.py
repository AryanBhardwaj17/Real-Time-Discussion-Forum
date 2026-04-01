"""Tag model and thread-tags association table."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


thread_tags_table = Table(
    "thread_tags",
    Base.metadata,
    Column("thread_id", UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True),
)
