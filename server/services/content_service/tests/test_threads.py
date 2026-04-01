"""Thread CRUD tests."""

import uuid
import pytest

from .helpers import auth_headers, USER2_ID, create_thread


class TestCreateThread:
    @pytest.mark.asyncio
    async def test_success(self, client, unique):
        resp = await client.post("/api/v1/threads", json={
            "title": f"Test Thread {unique}", "description": "A test thread body",
            "tags": ["python", "testing"],
        }, headers=auth_headers())
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == f"Test Thread {unique}"
        assert data["author_username"] == "testuser"
        assert set(data["tags"]) == {"python", "testing"}
        assert data["like_count"] == 0

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client):
        resp = await client.post("/api/v1/threads", json={"title": "Fail", "description": "x"})
        assert resp.status_code == 401


class TestGetThread:
    @pytest.mark.asyncio
    async def test_found(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.get(f"/api/v1/threads/{tid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == tid

    @pytest.mark.asyncio
    async def test_not_found(self, client):
        resp = await client.get(f"/api/v1/threads/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestListThreads:
    @pytest.mark.asyncio
    async def test_list(self, client, unique):
        await create_thread(client, unique)
        resp = await client.get("/api/v1/threads")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    @pytest.mark.asyncio
    async def test_sort_new(self, client):
        resp = await client.get("/api/v1/threads?sort=new")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_sort_top(self, client):
        resp = await client.get("/api/v1/threads?sort=top")
        assert resp.status_code == 200


class TestUpdateThread:
    @pytest.mark.asyncio
    async def test_owner_can_update(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.patch(f"/api/v1/threads/{tid}", json={"title": f"Updated {unique}"},
                                  headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["title"] == f"Updated {unique}"

    @pytest.mark.asyncio
    async def test_other_user_forbidden(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.patch(f"/api/v1/threads/{tid}", json={"title": "Hacked"},
                                  headers=auth_headers(user_id=USER2_ID, username="hacker"))
        assert resp.status_code == 403


class TestDeleteThread:
    @pytest.mark.asyncio
    async def test_owner_can_delete(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.delete(f"/api/v1/threads/{tid}", headers=auth_headers())
        assert resp.status_code == 200
        resp = await client.get(f"/api/v1/threads/{tid}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_other_user_forbidden(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.delete(f"/api/v1/threads/{tid}", headers=auth_headers(user_id=USER2_ID))
        assert resp.status_code == 403
