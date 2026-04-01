"""Content service business logic — re-exports from sub-modules."""

from app.services.threads import (
    get_thread_by_id,
    list_threads,
    create_thread,
    update_thread,
    delete_thread,
    toggle_pin,
    toggle_lock,
    recalculate_hot_score,
)
from app.services.comments import (
    get_comment_by_id,
    list_comments,
    list_replies,
    create_comment,
    update_comment,
    delete_comment,
    mask_deleted_comment,
)
from app.services.likes import (
    has_user_liked_thread,
    has_user_liked_comment,
    toggle_thread_like,
    toggle_comment_like,
    list_thread_likers,
    list_comment_likers,
)
from app.services.reports import (
    create_report,
    list_reports,
    resolve_report,
    enrich_reports_with_thread_id,
)
from app.services.internal import (
    get_content_stats,
    get_user_threads,
    get_user_comments,
    get_user_content_stats,
    get_recent_activity,
    reindex_all_threads,
    reconcile_counters,
)

__all__ = [
    # threads
    "get_thread_by_id", "list_threads", "create_thread", "update_thread",
    "delete_thread", "toggle_pin", "toggle_lock", "recalculate_hot_score",
    # comments
    "get_comment_by_id", "list_comments", "list_replies", "create_comment",
    "update_comment", "delete_comment", "mask_deleted_comment",
    # likes
    "has_user_liked_thread", "has_user_liked_comment", "toggle_thread_like",
    "toggle_comment_like", "list_thread_likers", "list_comment_likers",
    # reports
    "create_report", "list_reports", "resolve_report", "enrich_reports_with_thread_id",
    # internal
    "get_content_stats", "get_user_threads", "get_user_comments",
    "get_user_content_stats", "get_recent_activity", "reindex_all_threads",
    "reconcile_counters",
]
