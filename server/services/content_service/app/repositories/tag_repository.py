"""Tag repository — tag data access."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tag
from app.services.helpers import _sanitize


class TagRepository:
    """Encapsulates all database operations for the Tag model."""

    @staticmethod
    async def get_or_create_many(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
        if not tag_names:
            return []
        normalized = list({_sanitize(t).lower().strip() for t in tag_names if t.strip()})
        if not normalized:
            return []
        result = await db.execute(select(Tag).where(Tag.name.in_(normalized)))
        existing = {t.name: t for t in result.scalars().all()}
        tags = []
        for name in normalized:
            if name in existing:
                tags.append(existing[name])
            else:
                tag = Tag(name=name)
                db.add(tag)
                tags.append(tag)
        await db.flush()
        return tags

    @staticmethod
    async def increment_usage(db: AsyncSession, tag_id) -> None:
        await db.execute(update(Tag).where(Tag.id == tag_id).values(usage_count=Tag.usage_count + 1))

    @staticmethod
    async def decrement_usage(db: AsyncSession, tag_id) -> None:
        await db.execute(update(Tag).where(Tag.id == tag_id).values(usage_count=Tag.usage_count - 1))
