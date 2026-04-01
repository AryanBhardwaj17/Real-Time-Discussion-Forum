"""Content service routes — re-exports all routers."""

from app.routes.threads import threads_router
from app.routes.comments import comments_router
from app.routes.reports import reports_router
from app.routes.internal import internal_router
from app.routes.profiles import profile_router

__all__ = [
    "threads_router",
    "comments_router",
    "reports_router",
    "internal_router",
    "profile_router",
]
