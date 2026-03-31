"""Auth service core — configuration, database, dependencies, Redis."""

from app.core.config import Settings, get_settings
from app.db import engine, async_session_factory, create_tables, get_db
from app.core.deps import (
    CurrentUser, DbSession, AdminUser,
    get_current_user, get_current_user_id, require_role,
)
from app.core.redis import (
    connect_redis, disconnect_redis, get_redis, publish, stream_add,
)

__all__ = [
    "Settings", "get_settings",
    "engine", "async_session_factory", "create_tables", "get_db",
    "CurrentUser", "DbSession", "AdminUser",
    "get_current_user", "get_current_user_id", "require_role",
    "connect_redis", "disconnect_redis", "get_redis", "publish", "stream_add",
]
