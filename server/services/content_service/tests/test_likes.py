"""Like / unlike tests — threads and comments."""

import pytest

from .helpers import auth_headers, USER2_ID, create_thread


class TestThreadLike:
    @pytest.mark.asyncio
    async def test_toggle(self, client, unique):
        tid = await create_thread(client, unique)
        r1 = await client.post(f"/api/v1/threads/{tid}/like", headers=auth_headers(user_id=USER2_ID))
        assert r1.json()["liked"] is True
        assert r1.json()["like_count"] == 1
        r2 = await client.post(f"/api/v1/threads/{tid}/like", headers=auth_headers(user_id=USER2_ID))
        assert r2.json()["liked"] is False
        assert r2.json()["like_count"] == 0

    @pytest.mark.asyncio
    async def test_list_likers(self, client, unique):
        tid = await create_thread(client, unique)
        await client.post(f"/api/v1/threads/{tid}/like", headers=auth_headers(user_id=USER2_ID))
        resp = await client.get(f"/api/v1/threads/{tid}/likers")
        assert len(resp.json()["items"]) >= 1


class TestCommentLike:
    @pytest.mark.asyncio
    async def test_toggle(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Like me"},
                              headers=auth_headers())
        cid = r.json()["id"]
        resp = await client.post(f"/api/v1/comments/{cid}/like", headers=auth_headers(user_id=USER2_ID))
        assert resp.json()["liked"] is True
