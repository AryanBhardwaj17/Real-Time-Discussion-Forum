"""Moderator endpoint tests."""

import pytest

from .helpers import admin_headers, mod_headers, user_headers


class TestModActivity:
    @pytest.mark.asyncio
    async def test_moderator_access(self, client):
        resp = await client.get("/api/v1/dashboard/mod/activity", headers=mod_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "recent_threads" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_admin_allowed(self, client):
        resp = await client.get("/api/v1/dashboard/mod/activity", headers=admin_headers())
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_member_denied(self, client):
        resp = await client.get("/api/v1/dashboard/mod/activity", headers=user_headers())
        assert resp.status_code == 403
