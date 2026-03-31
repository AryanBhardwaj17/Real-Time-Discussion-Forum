"""Auth service dependencies — user extraction from gateway headers."""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ForbiddenError, UnauthorizedError
from app.db import get_db
from app.models import User, UserRole


async def get_current_user_id(request: Request) -> uuid.UUID:
    """Extract user ID from X-User-ID header (set by gateway)."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise UnauthorizedError("Authentication required")
    try:
        return uuid.UUID(user_id)
    except ValueError:
        raise UnauthorizedError("Invalid user identity")


async def get_current_user(
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Load the full user object from DB using the gateway-injected user ID."""
    from app.services import get_user_by_id
    user = await get_user_by_id(db, user_id)
    if not user.is_active:
        raise UnauthorizedError("Account is deactivated")
    return user


def require_role(*roles: UserRole):
    """Dependency factory for role-based access control."""
    allowed = {r.value for r in roles}
    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise ForbiddenError(f"Requires: {', '.join(sorted(allowed))}")
        return user
    return _check


# Type aliases
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
