"""User repository — all user-related data access."""

import uuid
from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    """Encapsulates all database operations for the User model."""

    @staticmethod
    async def find_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_username(db: AsyncSession, username: str, *, active_only: bool = False) -> User | None:
        stmt = select(User).where(User.username == username)
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_email_or_username(db: AsyncSession, email: str, username: str) -> User | None:
        result = await db.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_login(db: AsyncSession, login: str) -> User | None:
        result = await db.execute(
            select(User).where(or_(User.email == login, User.username == login))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_duplicate_username(db: AsyncSession, username: str, exclude_id: uuid.UUID) -> User | None:
        result = await db.execute(
            select(User).where(User.username == username, User.id != exclude_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, user: User) -> User:
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def list_paginated(db: AsyncSession, *, cursor: datetime | None = None, limit: int = 20):
        stmt = select(User).order_by(User.created_at.desc()).limit(limit + 1)
        if cursor is not None:
            stmt = stmt.where(User.created_at < cursor)
        result = await db.execute(stmt)
        users = list(result.scalars().all())

        next_cursor = None
        if len(users) > limit:
            users = users[:limit]
            next_cursor = users[-1].created_at
        return users, next_cursor
