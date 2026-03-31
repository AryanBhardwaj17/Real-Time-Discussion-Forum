"""Health check and internal API tests."""

import pytest

INTERNAL_HEADERS = {"X-Internal-Secret": "forum_internal_secret"}


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "auth"


class TestInternalAPI:
    @pytest.mark.asyncio
    async def test_stats(self, client):
        resp = await client.get("/internal/stats", headers=INTERNAL_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total_users"] >= 0
