"""Auth microservice — user registration, login, token management, admin ops."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from shared.logging import setup_logging, get_logger
from shared.exception_handlers import register_exception_handlers
from shared.middleware import RequestIDMiddleware

from app.core.config import get_settings
from app.db import engine, create_tables

settings = get_settings()
logger = get_logger(__name__)


async def _seed_roles() -> None:
    """Ensure roles lookup table has default entries."""
    from app.db import async_session_factory
    from app.models import RoleLookup
    from sqlalchemy import select

    defaults = [
        ("admin", "Administrator"),
        ("moderator", "Moderator"),
        ("member", "Member"),
    ]
    async with async_session_factory() as session:
        for code, label in defaults:
            exists = await session.execute(select(RoleLookup).where(RoleLookup.code == code))
            if exists.scalar_one_or_none() is None:
                session.add(RoleLookup(code=code, label=label))
        await session.commit()
    logger.info("roles_seeded")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(json_logs=not settings.DEBUG, log_level="DEBUG" if settings.DEBUG else "INFO", service_name="auth")
    logger.info("auth_service_startup")

    await create_tables()

    # Seed roles lookup table
    await _seed_roles()

    # Seed default admin user
    from app.db import async_session_factory
    from app.services import seed_default_admin
    async with async_session_factory() as session:
        await seed_default_admin(session)

    # Connect Redis for pub/sub (audit events)
    from app.core.redis import connect_redis, disconnect_redis
    await connect_redis()

    yield

    await disconnect_redis()
    await engine.dispose()
    logger.info("auth_service_shutdown")


app = FastAPI(title="Auth Service", version="0.1.0", lifespan=lifespan)

# ── Middleware ───────────────────────────────────────────────────────
app.add_middleware(RequestIDMiddleware)

# ── Exception Handlers ───────────────────────────────────────────────
register_exception_handlers(app)

# ── Health ───────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "auth"}

# ── Routes ───────────────────────────────────────────────────────────
from app.routes import auth_router, users_router, admin_router, internal_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(internal_router)
