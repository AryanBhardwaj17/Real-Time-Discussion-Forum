"""Registration tests."""

import pytest

from .helpers import register_user


class TestRegister:
    @pytest.mark.asyncio
    async def test_success(self, client, unique):
        resp = await client.post("/api/v1/auth/register", json={
            "email": f"test_{unique}@example.com",
            "username": f"user_{unique}",
            "password": "StrongPass1!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == f"user_{unique}"
        assert data["role"] == "member"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_duplicate_email(self, client, unique):
        email = f"dup_{unique}@example.com"
        await client.post("/api/v1/auth/register", json={
            "email": email, "username": f"u1_{unique}", "password": "StrongPass1!",
        })
        resp = await client.post("/api/v1/auth/register", json={
            "email": email, "username": f"u2_{unique}", "password": "StrongPass1!",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_duplicate_username(self, client, unique):
        username = f"dn_{unique}"
        await client.post("/api/v1/auth/register", json={
            "email": f"a_{unique}@example.com", "username": username, "password": "StrongPass1!",
        })
        resp = await client.post("/api/v1/auth/register", json={
            "email": f"b_{unique}@example.com", "username": username, "password": "StrongPass1!",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_weak_password(self, client, unique):
        resp = await client.post("/api/v1/auth/register", json={
            "email": f"w_{unique}@example.com", "username": f"w_{unique}", "password": "short",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_username(self, client, unique):
        resp = await client.post("/api/v1/auth/register", json={
            "email": f"i_{unique}@example.com", "username": "bad user!", "password": "StrongPass1!",
        })
        assert resp.status_code == 422
