"""Health check and internal API tests."""

import pytest

from .helpers import USER_ID, create_thread

INTERNAL_HEADERS = {"X-Internal-Secret": "forum_internal_secret"}


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "content"


class TestInternalAPI:
    @pytest.mark.asyncio
    async def test_content_stats(self, client):
        resp = await client.get("/internal/stats", headers=INTERNAL_HEADERS)
        assert resp.status_code == 200
        assert "total_threads" in resp.json()

    @pytest.mark.asyncio
    async def test_user_threads(self, client, unique):
        await create_thread(client, unique)
        resp = await client.get(f"/internal/users/{USER_ID}/threads", headers=INTERNAL_HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    @pytest.mark.asyncio
    async def test_user_content_stats(self, client):
        resp = await client.get(f"/internal/users/{USER_ID}/stats", headers=INTERNAL_HEADERS)
        assert resp.status_code == 200
        assert "thread_count" in resp.json()
