"""Search endpoint tests."""

import pytest


class TestSearchEndpoint:
    @pytest.mark.asyncio
    async def test_returns_results_or_empty(self, client):
        resp = await client.get("/api/v1/search/threads", params={"q": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "has_more" in data

    @pytest.mark.asyncio
    async def test_requires_query(self, client):
        resp = await client.get("/api/v1/search/threads")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        resp = await client.get("/api/v1/search/threads", params={"q": "test", "limit": 5})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 5

    @pytest.mark.asyncio
    async def test_cursor(self, client):
        resp = await client.get("/api/v1/search/threads", params={"q": "test", "cursor": "offset:0"})
        assert resp.status_code == 200


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "search"
