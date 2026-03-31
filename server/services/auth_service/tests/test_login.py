"""Login, logout, and token refresh tests."""

import pytest

from .helpers import register_user, login_user


class TestLogin:
    @pytest.mark.asyncio
    async def test_with_username(self, client, unique):
        await register_user(client, unique)
        resp = await client.post("/api/v1/auth/login", json={
            "login": f"u_{unique}", "password": "StrongPass1!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_with_email(self, client, unique):
        await register_user(client, unique)
        resp = await client.post("/api/v1/auth/login", json={
            "login": f"t_{unique}@example.com", "password": "StrongPass1!",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_wrong_password(self, client, unique):
        await register_user(client, unique)
        resp = await client.post("/api/v1/auth/login", json={
            "login": f"u_{unique}", "password": "Wrong!",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "login": "nobody", "password": "x",
        })
        assert resp.status_code == 401


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_success(self, client, unique):
        await register_user(client, unique)
        tokens = await login_user(client, unique)
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 200
        assert resp.json()["refresh_token"] != tokens["refresh_token"]

    @pytest.mark.asyncio
    async def test_reuse_detection(self, client, unique):
        await register_user(client, unique)
        tokens = await login_user(client, unique)
        old = tokens["refresh_token"]
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old})
        assert resp.status_code == 200
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "bogus"})
        assert resp.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_revokes_token(self, client, unique):
        await register_user(client, unique)
        tokens = await login_user(client, unique)
        resp = await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 200
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 401
