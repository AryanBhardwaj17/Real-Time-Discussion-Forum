"""Moderation tests — pin, lock, delete, and strict role hierarchy.

Rule: you can only moderate content authored by users with a *strictly lower*
role.  Same-level moderation (mod→mod, admin→admin) is forbidden.
"""

import uuid
import pytest

from .helpers import auth_headers, MOD_ID, create_thread


# ── Helpers ──────────────────────────────────────────────────────────

MOD2_ID = str(uuid.uuid4())
ADMIN_ID = str(uuid.uuid4())
ADMIN2_ID = str(uuid.uuid4())


async def _create_thread_as(client, unique, *, role, user_id, username):
    resp = await client.post("/api/v1/threads", json={
        "title": f"{role} Thread {unique}", "description": "body",
    }, headers=auth_headers(user_id=user_id, role=role, username=username))
    return resp.json()["id"]


async def _create_comment_as(client, thread_id, *, role, user_id, username):
    resp = await client.post(f"/api/v1/threads/{thread_id}/comments", json={
        "content": f"Comment by {role}",
    }, headers=auth_headers(user_id=user_id, role=role, username=username))
    return resp.json()["id"]


class TestPinLock:
    @pytest.mark.asyncio
    async def test_toggle_pin(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/pin",
                              headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert r.status_code == 200
        assert r.json()["is_pinned"] is True
        r2 = await client.post(f"/api/v1/threads/{tid}/pin",
                               headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert r2.json()["is_pinned"] is False

    @pytest.mark.asyncio
    async def test_toggle_lock(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/lock",
                              headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert r.status_code == 200
        assert r.json()["is_locked"] is True

    @pytest.mark.asyncio
    async def test_pin_forbidden_member(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.post(f"/api/v1/threads/{tid}/pin", headers=auth_headers())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_comment_on_locked_thread(self, client, unique):
        tid = await create_thread(client, unique)
        await client.post(f"/api/v1/threads/{tid}/lock",
                          headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        resp = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Fail"},
                                 headers=auth_headers())
        assert resp.status_code == 403


class TestDeleteHierarchy:
    """Delete: only allowed when actor role is strictly above author role."""

    # ── member content ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_mod_can_delete_member_thread(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_delete_member_thread(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_delete_member_comment(self, client, unique):
        tid = await create_thread(client, unique)
        cid = await _create_comment_as(client, tid, role="member", user_id=str(uuid.uuid4()), username="member2")
        resp = await client.delete(f"/api/v1/comments/{cid}",
                                   headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200

    # ── moderator content ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_admin_can_delete_mod_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod")
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_delete_mod_comment(self, client, unique):
        tid = await create_thread(client, unique)
        cid = await _create_comment_as(client, tid, role="moderator", user_id=MOD_ID, username="mod")
        resp = await client.delete(f"/api/v1/comments/{cid}",
                                   headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_mod_cannot_delete_mod_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod1")
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=MOD2_ID, role="moderator", username="mod2"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_mod_cannot_delete_mod_comment(self, client, unique):
        tid = await create_thread(client, unique)
        cid = await _create_comment_as(client, tid, role="moderator", user_id=MOD_ID, username="mod1")
        resp = await client.delete(f"/api/v1/comments/{cid}",
                                   headers=auth_headers(user_id=MOD2_ID, role="moderator", username="mod2"))
        assert resp.status_code == 403

    # ── admin content ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_mod_cannot_delete_admin_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin")
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_mod_cannot_delete_admin_comment(self, client, unique):
        tid = await create_thread(client, unique)
        cid = await _create_comment_as(client, tid, role="admin", user_id=ADMIN_ID, username="admin")
        resp = await client.delete(f"/api/v1/comments/{cid}",
                                   headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_admin_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin1")
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=ADMIN2_ID, role="admin", username="admin2"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_admin_comment(self, client, unique):
        tid = await create_thread(client, unique)
        cid = await _create_comment_as(client, tid, role="admin", user_id=ADMIN_ID, username="admin1")
        resp = await client.delete(f"/api/v1/comments/{cid}",
                                   headers=auth_headers(user_id=ADMIN2_ID, role="admin", username="admin2"))
        assert resp.status_code == 403

    # ── own content always deletable ─────────────────────────────

    @pytest.mark.asyncio
    async def test_mod_can_delete_own_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod")
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_delete_own_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin")
        resp = await client.delete(f"/api/v1/threads/{tid}",
                                   headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200


class TestPinLockHierarchy:
    """Pin/lock: only allowed when actor role is strictly above author role."""

    # ── mod pinning/locking member content (allowed) ─────────────

    @pytest.mark.asyncio
    async def test_mod_can_pin_member_thread(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.post(f"/api/v1/threads/{tid}/pin",
                                 headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 200
        assert resp.json()["is_pinned"] is True

    @pytest.mark.asyncio
    async def test_mod_can_lock_member_thread(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.post(f"/api/v1/threads/{tid}/lock",
                                 headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 200
        assert resp.json()["is_locked"] is True

    # ── mod cannot pin/lock moderator or admin content ───────────

    @pytest.mark.asyncio
    async def test_mod_cannot_pin_mod_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod1")
        resp = await client.post(f"/api/v1/threads/{tid}/pin",
                                 headers=auth_headers(user_id=MOD2_ID, role="moderator", username="mod2"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_mod_cannot_lock_mod_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod1")
        resp = await client.post(f"/api/v1/threads/{tid}/lock",
                                 headers=auth_headers(user_id=MOD2_ID, role="moderator", username="mod2"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_mod_cannot_pin_admin_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin")
        resp = await client.post(f"/api/v1/threads/{tid}/pin",
                                 headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 403

    # ── admin can pin/lock moderator content (allowed) ───────────

    @pytest.mark.asyncio
    async def test_admin_can_pin_mod_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod")
        resp = await client.post(f"/api/v1/threads/{tid}/pin",
                                 headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_lock_mod_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod")
        resp = await client.post(f"/api/v1/threads/{tid}/lock",
                                 headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200

    # ── admin cannot pin/lock admin content ──────────────────────

    @pytest.mark.asyncio
    async def test_admin_cannot_pin_admin_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin1")
        resp = await client.post(f"/api/v1/threads/{tid}/pin",
                                 headers=auth_headers(user_id=ADMIN2_ID, role="admin", username="admin2"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_lock_admin_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin1")
        resp = await client.post(f"/api/v1/threads/{tid}/lock",
                                 headers=auth_headers(user_id=ADMIN2_ID, role="admin", username="admin2"))
        assert resp.status_code == 403

    # ── own thread: mod/admin can always pin/lock own thread ─────

    @pytest.mark.asyncio
    async def test_mod_can_pin_own_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod")
        resp = await client.post(f"/api/v1/threads/{tid}/pin",
                                 headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 200
        assert resp.json()["is_pinned"] is True

    @pytest.mark.asyncio
    async def test_mod_can_lock_own_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="moderator", user_id=MOD_ID, username="mod")
        resp = await client.post(f"/api/v1/threads/{tid}/lock",
                                 headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 200
        assert resp.json()["is_locked"] is True

    @pytest.mark.asyncio
    async def test_admin_can_pin_own_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin")
        resp = await client.post(f"/api/v1/threads/{tid}/pin",
                                 headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200
        assert resp.json()["is_pinned"] is True

    @pytest.mark.asyncio
    async def test_admin_can_lock_own_thread(self, client, unique):
        tid = await _create_thread_as(client, unique, role="admin", user_id=ADMIN_ID, username="admin")
        resp = await client.post(f"/api/v1/threads/{tid}/lock",
                                 headers=auth_headers(user_id=ADMIN_ID, role="admin", username="admin"))
        assert resp.status_code == 200
        assert resp.json()["is_locked"] is True
