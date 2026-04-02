"""Mark-as-read tests."""

import uuid
import pytest

from .helpers import user_headers, seed_notification


class TestMarkSingleRead:
    @pytest.mark.asyncio
    async def test_mark_single(self, client):
        uid = str(uuid.uuid4())
        seed_notification(uid)
        resp = await client.get("/api/v1/notifications", headers=user_headers(uid))
        nid = resp.json()["items"][0]["id"]
        resp = await client.post(f"/api/v1/notifications/{nid}/read", headers=user_headers(uid))
        assert resp.status_code == 200


class TestMarkAllRead:
    @pytest.mark.asyncio
    async def test_mark_all(self, client):
        uid = str(uuid.uuid4())
        seed_notification(uid)
        seed_notification(uid)
        resp = await client.post("/api/v1/notifications/read-all", headers=user_headers(uid))
        assert resp.status_code == 200
        resp = await client.get("/api/v1/notifications/unread-count", headers=user_headers(uid))
        assert resp.json()["count"] == 0
