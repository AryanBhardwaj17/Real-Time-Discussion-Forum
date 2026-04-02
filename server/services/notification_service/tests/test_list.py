"""Notification listing tests."""

import uuid
import pytest

from .helpers import user_headers, seed_notification


class TestListNotifications:
    @pytest.mark.asyncio
    async def test_empty(self, client):
        resp = await client.get("/api/v1/notifications", headers=user_headers(str(uuid.uuid4())))
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_with_data(self, client):
        uid = str(uuid.uuid4())
        seed_notification(uid)
        resp = await client.get("/api/v1/notifications", headers=user_headers(uid))
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client):
        resp = await client.get("/api/v1/notifications")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unread_only(self, client):
        uid = str(uuid.uuid4())
        seed_notification(uid)
        seed_notification(uid, is_read=True)
        resp = await client.get("/api/v1/notifications?unread_only=true", headers=user_headers(uid))
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["is_read"] is False


class TestUnreadCount:
    @pytest.mark.asyncio
    async def test_count(self, client):
        uid = str(uuid.uuid4())
        seed_notification(uid)
        seed_notification(uid)
        resp = await client.get("/api/v1/notifications/unread-count", headers=user_headers(uid))
        assert resp.status_code == 200
        assert resp.json()["count"] >= 2
