"""Auth service helpers — audit events, user status publishing."""

import json
import uuid

from shared.logging import get_logger

logger = get_logger(__name__)


async def _publish_audit_event(
    actor_id: uuid.UUID, action: str, target_type: str, target_id: uuid.UUID, details: dict
) -> None:
    """Publish audit event to Redis for the dashboard service to consume."""
    try:
        from app.core.redis import get_redis
        r = get_redis()
        event = {
            "actor_id": str(actor_id),
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "details": details,
        }
        await r.publish("audit:events", json.dumps(event))
    except Exception:
        logger.warning("failed_to_publish_audit_event", action=action)


async def _publish_user_status_change(user_id: uuid.UUID, is_active: bool) -> None:
    """Publish user active status change to stream:user_updates for content service."""
    try:
        from app.core.redis import stream_add, publish
        await stream_add("stream:user_updates", {
            "event": "user_status_changed",
            "user_id": str(user_id),
            "is_active": is_active,
        })
        if not is_active:
            await publish(f"user:{user_id}", {"type": "force_logout"})
    except Exception:
        logger.exception("failed_to_publish_user_status_change", user_id=str(user_id))
