"""Token repository — RefreshToken data access."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


class TokenRepository:
    """Encapsulates all database operations for token models."""

    # ── Refresh Tokens ───────────────────────────────────────────

    @staticmethod
    async def find_refresh_by_hash(db: AsyncSession, token_hash: str, *, for_update: bool = False) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        if for_update:
            stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_refresh(db: AsyncSession, token: RefreshToken) -> RefreshToken:
        db.add(token)
        await db.flush()
        return token

    @staticmethod
    async def revoke_all_user_refresh(db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )

    @staticmethod
    async def revoke_by_hash(db: AsyncSession, token_hash: str) -> None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )
