"""Report creation and management tests."""

import pytest

from .helpers import auth_headers, USER2_ID, MOD_ID, create_thread


class TestCreateReport:
    @pytest.mark.asyncio
    async def test_report_thread(self, client, unique):
        tid = await create_thread(client, unique)
        resp = await client.post(f"/api/v1/threads/{tid}/report", json={"reason": "spam"},
                                 headers=auth_headers(user_id=USER2_ID))
        assert resp.status_code == 201
        assert resp.json()["reason"] == "spam"

    @pytest.mark.asyncio
    async def test_report_comment(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/comments", json={"content": "Bad"},
                              headers=auth_headers())
        cid = r.json()["id"]
        resp = await client.post(f"/api/v1/comments/{cid}/report", json={"reason": "harassment"},
                                 headers=auth_headers(user_id=USER2_ID))
        assert resp.status_code == 201


class TestReportManagement:
    @pytest.mark.asyncio
    async def test_list_reports(self, client, unique):
        tid = await create_thread(client, unique)
        await client.post(f"/api/v1/threads/{tid}/report", json={"reason": "spam"},
                          headers=auth_headers(user_id=USER2_ID))
        resp = await client.get("/api/v1/reports?status=pending",
                                headers=auth_headers(user_id=MOD_ID, role="admin", username="admin"))
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    @pytest.mark.asyncio
    async def test_resolve_report(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/report", json={"reason": "spam"},
                              headers=auth_headers(user_id=USER2_ID))
        report = r.json()
        resp = await client.post(f"/api/v1/reports/{report['id']}/resolve",
                                 json={"action": "resolved"},
                                 headers=auth_headers(user_id=MOD_ID, role="admin", username="admin"))
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_dismiss_report(self, client, unique):
        tid = await create_thread(client, unique)
        r = await client.post(f"/api/v1/threads/{tid}/report", json={"reason": "other"},
                              headers=auth_headers(user_id=USER2_ID))
        report = r.json()
        resp = await client.post(f"/api/v1/reports/{report['id']}/resolve",
                                 json={"action": "dismissed"},
                                 headers=auth_headers(user_id=MOD_ID, role="moderator", username="mod"))
        assert resp.status_code == 200
        assert resp.json()["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_list_reports_forbidden_member(self, client):
        resp = await client.get("/api/v1/reports", headers=auth_headers())
        assert resp.status_code == 403
