"""Health check and ConnectionManager unit tests."""

import pytest

from main import ConnectionManager


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "realtime"
        assert "connections" in data


class TestConnectionManager:
    def test_initial_state(self):
        mgr = ConnectionManager()
        assert mgr.active_connections == 0

    def test_disconnect_unknown_ws(self):
        mgr = ConnectionManager()
        mgr.disconnect(object())
