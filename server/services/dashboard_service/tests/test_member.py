"""Member /me endpoint tests."""

import pytest

from .helpers import user_headers


class TestMyThreads:
    @pytest.mark.asyncio
    async def test_list(self, client):
        resp = await client.get("/api/v1/dashboard/me/threads", headers=user_headers())
        assert resp.status_code == 200
        assert "items" in resp.json()


class TestMyComments:
    @pytest.mark.asyncio
    async def test_list(self, client):
        resp = await client.get("/api/v1/dashboard/me/comments", headers=user_headers())
        assert resp.status_code == 200
        assert "items" in resp.json()


class TestMyStats:
    @pytest.mark.asyncio
    async def test_stats(self, client):
        resp = await client.get("/api/v1/dashboard/me/stats", headers=user_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "thread_count" in data
        assert "comment_count" in data


class TestUnauthenticated:
    @pytest.mark.asyncio
    async def test_unauthenticated(self, client):
        resp = await client.get("/api/v1/dashboard/me/threads")
        assert resp.status_code == 401
