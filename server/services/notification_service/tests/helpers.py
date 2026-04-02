"""Shared test helpers for notification service."""

import json
import time
import uuid
import httpx
import redis

BASE = "http://localhost:8003"
REDIS_URL = "redis://:forum_redis_pass@forum_redis:6379/0"
ACTOR_ID = str(uuid.uuid4())


def user_headers(user_id):
    return {"X-User-ID": user_id, "X-User-Role": "member"}


def seed_notification(user_id, is_read=False):
    """Push a notification into the Redis stream and wait for processing."""
    r = redis.from_url(REDIS_URL)
    r.xadd("stream:notifications", {"payload": json.dumps({
        "user_id": user_id,
        "actor_id": ACTOR_ID,
        "notification_type": "reply",
        "reference_type": "comment",
        "reference_id": str(uuid.uuid4()),
        "content": "Someone replied",
    })})
    r.close()
    time.sleep(1.5)
    if is_read:
        with httpx.Client(base_url=BASE) as c:
            c.post("/api/v1/notifications/read-all", headers=user_headers(user_id))
