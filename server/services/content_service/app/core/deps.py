"""Content service dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ForbiddenError, UnauthorizedError
from app.db import get_db


async def get_current_user_id(request: Request) -> uuid.UUID:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise UnauthorizedError("Authentication required")
    return uuid.UUID(user_id)


class UserContext:
    """Lightweight user representation assembled from gateway headers."""

    def __init__(self, user_id: uuid.UUID, role: str, username: str):
        self.id = user_id
        self.role = role
        self.username = username


async def get_user_context(request: Request) -> UserContext:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise UnauthorizedError("Authentication required")
    return UserContext(
        user_id=uuid.UUID(user_id),
        role=request.headers.get("X-User-Role", "member"),
        username=request.headers.get("X-User-Username", ""),
    )


def require_moderator(request: Request) -> UserContext:
    """Require admin or moderator role."""
    user_id = request.headers.get("X-User-ID")
    role = request.headers.get("X-User-Role", "member")
    if not user_id:
        raise UnauthorizedError("Authentication required")
    if role not in ("admin", "moderator"):
        raise ForbiddenError("Requires admin or moderator role")
    return UserContext(
        user_id=uuid.UUID(user_id),
        role=role,
        username=request.headers.get("X-User-Username", ""),
    )


# Type aliases
DbSession = Annotated[AsyncSession, Depends(get_db)]
AuthUser = Annotated[UserContext, Depends(get_user_context)]
ModUser = Annotated[UserContext, Depends(require_moderator)]
