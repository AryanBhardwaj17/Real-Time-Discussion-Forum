"""Comment CRUD tests."""

import uuid
import pytest

from .helpers import auth_headers, USER2_ID, create_thread


class TestCreateComment:
    @pytest.mark.asyncio
    async def test_create(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Great!"},
                                 headers=auth_headers())
        assert resp.status_code == 201
        assert resp.json()["depth"] == 0

    @pytest.mark.asyncio
    async def test_reply(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Parent"},
                              headers=auth_headers())
        cid = r.json()["id"]
        resp = await client.post(f"/api/v1/threads/{tid}/comments",
                                 json={"content": "Reply", "parent_id": cid},
                                 headers=auth_headers(user_id=USER2_ID, username="user2"))
        assert resp.status_code == 201
        assert resp.json()["depth"] == 1

    @pytest.mark.asyncio
    async def test_on_nonexistent_thread(self, client):
        resp = await client.post(f"/api/v1/threads/{uuid.uuid4()}/comments", json={"content": "X"},
                                 headers=auth_headers())
        assert resp.status_code == 404


class TestListComments:
    @pytest.mark.asyncio
    async def test_list(self, client, unique):
        tid = await create_thread(client, unique)
        await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "C1"}, headers=auth_headers())
        resp = await client.get(f"/api/v1/threads/{tid}/comments")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    @pytest.mark.asyncio
    async def test_replies(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "P"},
                              headers=auth_headers())
        cid = r.json()["id"]
        await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "R", "parent_id": cid},
                          headers=auth_headers())
        resp = await client.get(f"/api/v1/comments/{cid}/replies")
        assert len(resp.json()["items"]) >= 1


class TestUpdateComment:
    @pytest.mark.asyncio
    async def test_owner_can_update(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Old"},
                              headers=auth_headers())
        cid = r.json()["id"]
        resp = await client.patch(f"/api/v1/comments/{cid}", json={"content": "New"}, headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["content"] == "New"

    @pytest.mark.asyncio
    async def test_other_user_forbidden(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Mine"},
                              headers=auth_headers())
        cid = r.json()["id"]
        resp = await client.patch(f"/api/v1/comments/{cid}", json={"content": "Hacked"},
                                  headers=auth_headers(user_id=USER2_ID))
        assert resp.status_code == 403


class TestDeleteComment:
    @pytest.mark.asyncio
    async def test_owner_can_delete(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Del"},
                              headers=auth_headers())
        cid = r.json()["id"]
        resp = await client.delete(f"/api/v1/comments/{cid}", headers=auth_headers())
        assert resp.status_code == 200
