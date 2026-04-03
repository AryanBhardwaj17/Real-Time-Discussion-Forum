"""Admin endpoint tests — platform stats and audit log."""

import pytest

from .helpers import admin_headers, user_headers, seed_audit_log


class TestPlatformStats:
    @pytest.mark.asyncio
    async def test_success(self, client):
        resp = await client.get("/api/v1/dashboard/admin/stats", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "total_threads" in data
        assert "total_comments" in data

    @pytest.mark.asyncio
    async def test_requires_admin(self, client):
        resp = await client.get("/api/v1/dashboard/admin/stats", headers=user_headers())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client):
        resp = await client.get("/api/v1/dashboard/admin/stats")
        assert resp.status_code == 401


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_returns_entries(self, client):
        seed_audit_log()
        resp = await client.get("/api/v1/dashboard/admin/audit-log", headers=admin_headers())
        assert resp.status_code == 200
        assert "items" in resp.json()
        assert len(resp.json()["items"]) >= 1

    @pytest.mark.asyncio
    async def test_requires_admin(self, client):
        from .helpers import mod_headers
        resp = await client.get("/api/v1/dashboard/admin/audit-log", headers=mod_headers())
        assert resp.status_code == 403
