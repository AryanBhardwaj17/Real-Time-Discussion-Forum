"""Shared helpers for content service business logic."""

import json
import math
import re
import time
import uuid
from datetime import datetime, timezone

import bleach
import httpx

from shared.exceptions import ValidationError
from shared.logging import get_logger

from app.core.config import get_settings
from app.core.deps import UserContext
from app.core.redis import publish, stream_add

logger = get_logger(__name__)

ALLOWED_TAGS: list[str] = []
ALLOWED_ATTRS: dict[str, list[str]] = {}

MEILI_STREAM = "stream:meili_indexing"


# ═══════════════════════════════════════════════════════════════════
# Role Hierarchy
# ═══════════════════════════════════════════════════════════════════

_ROLE_LEVEL: dict[str, int] = {"member": 0, "moderator": 1, "admin": 2}


def _can_moderate(actor_role: str, author_role: str) -> bool:
    """Return True if *actor_role* is strictly above *author_role* in the hierarchy.

    Used for delete / pin / lock — a user may only moderate content authored
    by someone with a **lower** role.  Same-level moderation is forbidden.
    """
    return _ROLE_LEVEL.get(actor_role, 0) > _ROLE_LEVEL.get(author_role, 0)


def _sanitize(text: str) -> str:
    return bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def _compute_hot_score(likes: int, created_at: datetime) -> float:
    return math.log10(max(likes, 1)) + created_at.timestamp() / 45000


def _parse_cursor_dt(value: str) -> datetime:
    """Parse an ISO datetime cursor that may have '+' URL-decoded to space."""
    try:
        return datetime.fromisoformat(value.replace(" ", "+"))
    except (ValueError, TypeError):
        raise ValidationError("Invalid cursor format")


def _parse_cursor_dt_id(value: str) -> tuple[datetime, uuid.UUID]:
    """Parse a compound 'datetime|uuid' cursor for time-based pagination."""
    try:
        parts = value.split("|")
        dt = datetime.fromisoformat(parts[0].replace(" ", "+"))
        uid = uuid.UUID(parts[1])
        return dt, uid
    except (ValueError, TypeError, IndexError):
        raise ValidationError("Invalid cursor format")


# ═══════════════════════════════════════════════════════════════════
# Circuit Breaker (for inter-service HTTP calls)
# ═══════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """Simple circuit breaker: after N failures, stop calling for a cooldown."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0):
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._last_failure_time = 0.0
        self._state = "closed"

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if time.monotonic() - self._last_failure_time > self._reset_timeout:
                self._state = "half-open"
                return False
            return True
        return False

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = "open"


_auth_circuit = CircuitBreaker(failure_threshold=5, reset_timeout=30.0)


# ═══════════════════════════════════════════════════════════════════
# Meilisearch Helpers (queue-based via Redis Stream)
# ═══════════════════════════════════════════════════════════════════

def _thread_to_meili_doc(thread) -> dict:
    return {
        "id": str(thread.id),
        "title": thread.title,
        "description": thread.description,
        "author_id": str(thread.author_id),
        "author_username": thread.author_username,
        "tags": thread.tags or [],
        "like_count": thread.like_count,
        "comment_count": thread.comment_count,
        "hot_score": thread.hot_score,
        "is_pinned": thread.is_pinned,
        "is_locked": thread.is_locked,
        "is_deleted": thread.is_deleted,
        "created_at": thread.created_at.timestamp(),
    }


async def _meili_index_thread(doc: dict) -> None:
    try:
        await stream_add(MEILI_STREAM, {"action": "index", "doc": json.dumps(doc)})
    except Exception:
        logger.warning("meili_queue_failed", action="index", doc_id=doc.get("id"))


async def _meili_delete_thread(thread_id: str) -> None:
    try:
        await stream_add(MEILI_STREAM, {"action": "delete", "thread_id": thread_id})
    except Exception:
        logger.warning("meili_queue_failed", action="delete", thread_id=thread_id)


async def _meili_update_thread(doc: dict) -> None:
    """Queue a partial update for the Meilisearch background worker."""
    try:
        await stream_add(MEILI_STREAM, {"action": "update", "doc": json.dumps(doc)})
    except Exception:
        logger.warning("meili_queue_failed", action="update", doc_id=doc.get("id"))


# ═══════════════════════════════════════════════════════════════════
# Redis Event Helpers
# ═══════════════════════════════════════════════════════════════════

_MENTION_RE = re.compile(r"@([A-Za-z0-9_]{1,50})(?:\s|$|[^A-Za-z0-9_])")


def _extract_mentions(text: str) -> set[str]:
    """Extract unique @usernames from text."""
    return {m.lower() for m in _MENTION_RE.findall(text)}


async def _resolve_usernames(usernames: set[str]) -> dict[str, str]:
    """Resolve usernames to user_ids via auth service (with circuit breaker)."""
    if not usernames:
        return {}
    if _auth_circuit.is_open:
        logger.warning("auth_circuit_open_skipping_mention_resolution")
        return {}
    try:
        settings = get_settings()
        internal_headers: dict[str, str] = {}
        if settings.INTERNAL_SECRET:
            internal_headers["X-Internal-Secret"] = settings.INTERNAL_SECRET
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.AUTH_SERVICE_URL}/internal/users/lookup-usernames",
                json={"usernames": list(usernames)},
                headers=internal_headers,
            )
            resp.raise_for_status()
            _auth_circuit.record_success()
            return resp.json().get("users", {})
    except Exception:
        _auth_circuit.record_failure()
        logger.warning("mention_resolution_failed", circuit_state=_auth_circuit._state)
        return {}


async def _send_mention_notifications(*, text: str, actor: UserContext, reference_type: str, reference_id: str, thread_id: str | None = None, exclude_user_ids: set[str] | None = None) -> None:
    """Parse @mentions from text and send notification to each mentioned user."""
    mentions = _extract_mentions(text)
    if not mentions:
        return
    resolved = await _resolve_usernames(mentions)
    exclude = exclude_user_ids or set()
    for username, uid in resolved.items():
        if uid in exclude:
            continue
        await _publish_notification_event(
            user_id=uid, actor_id=str(actor.id),
            notification_type="mention", reference_type=reference_type,
            reference_id=reference_id, thread_id=thread_id,
            content=f"@{actor.username} mentioned you in a {reference_type}",
        )


async def _publish_notification_event(*, user_id: str, actor_id: str, notification_type: str, reference_type: str, reference_id: str, content: str, thread_id: str | None = None) -> None:
    """Publish notification event to Redis Stream for the Notification service."""
    if user_id == actor_id:
        return
    try:
        await stream_add("stream:notifications", {
            "user_id": user_id,
            "actor_id": actor_id,
            "notification_type": notification_type,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "thread_id": thread_id,
            "content": content,
        })
    except Exception:
        logger.exception("failed_to_publish_notification_event")


async def _publish_notification_retraction(*, user_id: str, actor_id: str, notification_type: str, reference_id: str) -> None:
    """Publish retraction event to remove a stale notification (e.g. on unlike)."""
    if user_id == actor_id:
        return
    try:
        await stream_add("stream:notifications", {
            "action": "retract",
            "user_id": user_id,
            "actor_id": actor_id,
            "notification_type": notification_type,
            "reference_id": reference_id,
        })
    except Exception:
        logger.exception("failed_to_publish_notification_retraction")


async def _publish_audit_event(actor_id: uuid.UUID, action: str, target_type: str, target_id: uuid.UUID, details: dict) -> None:
    """Publish audit event to Redis Stream for the Dashboard service."""
    try:
        await stream_add("stream:audit", {
            "actor_id": str(actor_id), "action": action,
            "target_type": target_type, "target_id": str(target_id), "details": details,
        })
    except Exception:
        logger.exception("failed_to_publish_audit_event")
