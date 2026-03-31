"""Profile and password management tests."""

import pytest

from .helpers import register_user, login_user, user_id_from_jwt, auth_headers


class TestProfile:
    @pytest.mark.asyncio
    async def test_get_profile(self, client, unique):
        await register_user(client, unique)
        tokens = await login_user(client, unique)
        uid = user_id_from_jwt(tokens)
        resp = await client.get("/api/v1/users/me", headers=auth_headers(uid))
        assert resp.status_code == 200
        assert resp.json()["username"] == f"u_{unique}"

    @pytest.mark.asyncio
    async def test_update_profile(self, client, unique):
        await register_user(client, unique)
        tokens = await login_user(client, unique)
        uid = user_id_from_jwt(tokens)
        resp = await client.patch("/api/v1/users/me", json={"name": "New", "bio": "hello"},
                                  headers=auth_headers(uid))
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


class TestPublicProfile:
    @pytest.mark.asyncio
    async def test_get(self, client, unique):
        await register_user(client, unique)
        resp = await client.get(f"/api/v1/users/u_{unique}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == f"u_{unique}"
        assert "email" not in data
        assert "id" in data
        assert "role" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_not_found(self, client):
        resp = await client.get("/api/v1/users/nonexistent_user_xyz")
        assert resp.status_code == 404


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_success(self, client, unique):
        await register_user(client, unique)
        tokens = await login_user(client, unique)
        uid = user_id_from_jwt(tokens)
        resp = await client.post("/api/v1/auth/change-password", json={
            "current_password": "StrongPass1!", "new_password": "NewPass456!",
        }, headers=auth_headers(uid))
        assert resp.status_code == 200
        resp = await client.post("/api/v1/auth/login", json={
            "login": f"u_{unique}", "password": "NewPass456!",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_wrong_current(self, client, unique):
        await register_user(client, unique)
        tokens = await login_user(client, unique)
        uid = user_id_from_jwt(tokens)
        resp = await client.post("/api/v1/auth/change-password", json={
            "current_password": "wrong!", "new_password": "NewPass456!",
        }, headers=auth_headers(uid))
        assert resp.status_code == 422
