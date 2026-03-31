"""Auth service routes — re-exports all routers."""

from app.routes.auth import auth_router
from app.routes.users import users_router
from app.routes.admin import admin_router
from app.routes.internal import internal_router

__all__ = [
    "auth_router",
    "users_router",
    "admin_router",
    "internal_router",
]
