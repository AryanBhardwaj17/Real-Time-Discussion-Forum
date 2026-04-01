"""Shared test helpers for content service — importable by all test modules."""

import uuid

USER_ID = str(uuid.uuid4())
USER2_ID = str(uuid.uuid4())
MOD_ID = str(uuid.uuid4())


def auth_headers(user_id=USER_ID, role="member", username="testuser"):
    """Build fake gateway-injected auth headers."""
    return {"X-User-ID": user_id, "X-User-Role": role, "X-User-Username": username}


async def create_thread(client, unique, *, user_id=USER_ID, role="member", username="testuser"):
    """Helper — create a thread and return its ID."""
    resp = await client.post("/api/v1/threads", json={
        "title": f"Thread {unique}", "description": "body",
    }, headers=auth_headers(user_id=user_id, role=role, username=username))
    return resp.json()["id"]
