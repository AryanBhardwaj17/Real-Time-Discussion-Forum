"""Internal routes — for Dashboard service, not exposed through gateway."""

from fastapi import APIRouter, Depends, Request

from shared.exceptions import ForbiddenError
from app.core.config import get_settings
from app.core.deps import DbSession

internal_router = APIRouter(prefix="/internal", tags=["Internal"])


async def _verify_internal_secret(request: Request) -> None:
    """Verify the caller provides the shared internal secret."""
    settings = get_settings()
    if not settings.INTERNAL_SECRET:
        raise ForbiddenError("Internal secret not configured")
    provided = request.headers.get("X-Internal-Secret", "")
    if provided != settings.INTERNAL_SECRET:
        raise ForbiddenError("Invalid internal secret")


@internal_router.get("/stats", dependencies=[Depends(_verify_internal_secret)])
async def internal_stats(db: DbSession) -> dict:
    """Return user aggregate stats for the dashboard service."""
    from sqlalchemy import func, select
    from app.models import User

    total = (await db.execute(select(func.count(User.id)))).scalar_one()
    active = (await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))).scalar_one()
    return {"total_users": total, "active_users": active}


@internal_router.post("/users/lookup-usernames", dependencies=[Depends(_verify_internal_secret)])
async def lookup_usernames(body: dict, db: DbSession) -> dict:
    """Resolve a list of usernames to user IDs (for @mention support)."""
    from sqlalchemy import select
    from app.models import User

    usernames = body.get("usernames", [])
    if not usernames or not isinstance(usernames, list):
        return {"users": {}}
    # Limit to 20 usernames per request
    usernames = [u.lower() for u in usernames[:20]]
    result = await db.execute(
        select(User.id, User.username).where(
            User.username.in_(usernames), User.is_active.is_(True)
        )
    )
    users = {row.username: str(row.id) for row in result.all()}
    return {"users": users}
