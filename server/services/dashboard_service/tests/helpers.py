"""Shared test helpers for dashboard service."""

import json
import time
import uuid
import redis

REDIS_URL = "redis://:forum_redis_pass@forum_redis:6379/0"

ADMIN_ID = str(uuid.uuid4())
MOD_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def admin_headers():
    return {"X-User-ID": ADMIN_ID, "X-User-Role": "admin"}


def mod_headers():
    return {"X-User-ID": MOD_ID, "X-User-Role": "moderator"}


def user_headers():
    return {"X-User-ID": USER_ID, "X-User-Role": "member"}


def seed_audit_log():
    """Push a test entry into the Redis audit stream."""
    r = redis.from_url(REDIS_URL)
    r.xadd("stream:audit", {"payload": json.dumps({
        "actor_id": ADMIN_ID,
        "action": "test_action",
        "target_type": "thread",
        "target_id": str(uuid.uuid4()),
        "details": {"test": True},
    })})
    r.close()
    time.sleep(0.5)
