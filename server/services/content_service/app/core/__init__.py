"""Content service core — configuration, database, dependencies, Redis, Meilisearch."""

from app.core.config import Settings, get_settings
from app.db import engine, async_session_factory, create_tables, get_db
from app.core.deps import (
    DbSession, AuthUser, ModUser, UserContext,
    get_current_user_id, get_user_context, require_moderator,
)
from app.core.redis import connect_redis, disconnect_redis, get_redis, publish, stream_add
from app.core.meilisearch import connect_meili, disconnect_meili, get_meili, THREADS_INDEX

__all__ = [
    "Settings", "get_settings",
    "engine", "async_session_factory", "create_tables", "get_db",
    "DbSession", "AuthUser", "ModUser", "UserContext",
    "get_current_user_id", "get_user_context", "require_moderator",
    "connect_redis", "disconnect_redis", "get_redis", "publish", "stream_add",
    "connect_meili", "disconnect_meili", "get_meili", "THREADS_INDEX",
]
