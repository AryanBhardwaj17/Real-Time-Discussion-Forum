"""Frontend E2E smoke tests — verifies all API flows the React app uses.

Tests go through the Vite dev-server proxy (same as the browser would),
which proxies /api -> gateway:8000 and /ws -> ws://gateway:8000.

Usage:
    py tests/smoke_frontend_e2e.py [--base http://localhost:5176]
"""

import sys
import os
import json
import time
import http.cookiejar
import urllib.request
import urllib.error

# Force UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

BASE = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--base" else "http://localhost:5176"
PASS = 0
FAIL = 0
ts = str(int(time.time()))

# Cookie jar to persist HttpOnly cookies across requests (like a browser)
_cookie_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookie_jar))


def _req(method: str, path: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict | str]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with _opener.open(req, timeout=15) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label} — {detail}")


def main() -> None:
    global PASS, FAIL
    print("=" * 65)
    print(f"Frontend E2E Tests (via Vite proxy -> Gateway -> Services)")
    print(f"Base URL: {BASE}")
    print("=" * 65)

    # ── 1. Vite serves the SPA ───────────────────────────────────
    print("\n1. Vite Dev Server — serves SPA")
    code, body = _req("GET", "/")
    check("GET / returns 200", code == 200, f"got {code}")
    check("HTML contains root div", isinstance(body, str) and "root" in body, "")

    # ── 2. Auth: Register ────────────────────────────────────────
    print("\n2. Auth — Register (POST /api/v1/auth/register)")
    email = f"e2e_{ts}@test.com"
    username = f"e2euser{ts}"
    code, data = _req("POST", "/api/v1/auth/register", {
        "email": email,
        "username": username,
        "password": "TestPass123!",
    })
    check("Register → 201", code == 201, f"got {code}: {data}")
    user_id = data.get("id", "") if isinstance(data, dict) else ""
    check("Has user id", bool(user_id), str(data))
    check("Role is member", isinstance(data, dict) and data.get("role") == "member", str(data))

    # ── 3. Auth: Login ───────────────────────────────────────────
    print("\n3. Auth — Login (POST /api/v1/auth/login)")
    code, data = _req("POST", "/api/v1/auth/login", {
        "login": username,
        "password": "TestPass123!",
    })
    check("Login → 200", code == 200, f"got {code}: {data}")
    # Tokens are now in HttpOnly cookies, not in the response body
    has_access_cookie = any(c.name == "access_token" for c in _cookie_jar)
    has_refresh_cookie = any(c.name == "refresh_token" for c in _cookie_jar)
    check("Got access_token cookie", has_access_cookie, str([c.name for c in _cookie_jar]))
    check("Got refresh_token cookie", has_refresh_cookie, str([c.name for c in _cookie_jar]))

    # No need for auth headers — cookies are sent automatically

    # ── 4. Users: Get Profile ────────────────────────────────────
    print("\n4. Users — Profile (GET /api/v1/users/me)")
    code, data = _req("GET", "/api/v1/users/me")
    check("GET /users/me → 200", code == 200, f"got {code}: {data}")
    check("Username correct", isinstance(data, dict) and data.get("username") == username)

    # ── 5. Users: Update Profile ─────────────────────────────────
    print("\n5. Users — Update Profile (PATCH /api/v1/users/me)")
    code, data = _req("PATCH", "/api/v1/users/me", {"name": "E2E Tester", "bio": "Test bio"})
    check("PATCH /users/me → 200", code == 200, f"got {code}: {data}")
    check("Name updated", isinstance(data, dict) and data.get("name") == "E2E Tester")

    # ── 6. Threads: Create ───────────────────────────────────────
    print("\n6. Threads — Create (POST /api/v1/threads)")
    code, data = _req("POST", "/api/v1/threads", {
        "title": f"E2E Thread {ts}",
        "description": "End-to-end test thread for frontend validation.",
        "tags": ["e2e", "test"],
    })
    check("Create thread → 201", code == 201, f"got {code}: {data}")
    thread_id = data.get("id", "") if isinstance(data, dict) else ""
    check("Got thread id", bool(thread_id))

    # ── 7. Threads: List ─────────────────────────────────────────
    print("\n7. Threads — List (GET /api/v1/threads)")
    for sort in ["hot", "new", "top"]:
        code, data = _req("GET", f"/api/v1/threads?sort={sort}&limit=5")
        check(f"List threads sort={sort} → 200", code == 200, f"got {code}")
        check(f"  has items array", isinstance(data, dict) and isinstance(data.get("items"), list))

    # ── 8. Threads: Get Single ───────────────────────────────────
    print("\n8. Threads — Get (GET /api/v1/threads/:id)")
    if thread_id:
        code, data = _req("GET", f"/api/v1/threads/{thread_id}")
        check("Get thread → 200", code == 200)
        check("Title matches", isinstance(data, dict) and data.get("title") == f"E2E Thread {ts}")

    # ── 9. Threads: Update ───────────────────────────────────────
    print("\n9. Threads — Update (PATCH /api/v1/threads/:id)")
    if thread_id:
        code, data = _req("PATCH", f"/api/v1/threads/{thread_id}", {"description": "Updated desc"})
        check("Update thread → 200", code == 200, f"got {code}: {data}")

    # ── 10. Threads: Like Toggle ─────────────────────────────────
    print("\n10. Threads — Like (POST /api/v1/threads/:id/like)")
    if thread_id:
        code, data = _req("POST", f"/api/v1/threads/{thread_id}/like")
        check("Like thread → 200", code == 200, f"got {code}: {data}")
        check("Liked=true", isinstance(data, dict) and data.get("liked") is True)
        check("Like count > 0", isinstance(data, dict) and data.get("like_count", 0) > 0)
        # Unlike
        code, data = _req("POST", f"/api/v1/threads/{thread_id}/like")
        check("Unlike → liked=false", isinstance(data, dict) and data.get("liked") is False)

    # ── 11. Threads: Likers ──────────────────────────────────────
    print("\n11. Threads — Likers (GET /api/v1/threads/:id/likers)")
    if thread_id:
        # Re-like first
        _req("POST", f"/api/v1/threads/{thread_id}/like")
        code, data = _req("GET", f"/api/v1/threads/{thread_id}/likers")
        check("List likers → 200", code == 200, f"got {code}")

    # ── 12. Comments: Create ─────────────────────────────────────
    print("\n12. Comments — Create (POST /api/v1/threads/:id/comments)")
    comment_id = ""
    if thread_id:
        code, data = _req("POST", f"/api/v1/threads/{thread_id}/comments", {
            "content": "E2E test comment!",
        })
        check("Create comment → 201", code == 201, f"got {code}: {data}")
        comment_id = data.get("id", "") if isinstance(data, dict) else ""
        check("Got comment id", bool(comment_id))

    # ── 13. Comments: Reply (nested) ─────────────────────────────
    print("\n13. Comments — Reply (nested comment)")
    reply_id = ""
    if thread_id and comment_id:
        code, data = _req("POST", f"/api/v1/threads/{thread_id}/comments", {
            "content": "E2E reply to comment!",
            "parent_id": comment_id,
        })
        check("Create reply → 201", code == 201, f"got {code}: {data}")
        reply_id = data.get("id", "") if isinstance(data, dict) else ""
        check("Reply has depth=1", isinstance(data, dict) and data.get("depth") == 1)

    # ── 14. Comments: List ───────────────────────────────────────
    print("\n14. Comments — List (GET /api/v1/threads/:id/comments)")
    if thread_id:
        code, data = _req("GET", f"/api/v1/threads/{thread_id}/comments?sort=new&limit=50")
        check("List comments → 200", code == 200, f"got {code}")
        items = data.get("items", []) if isinstance(data, dict) else []
        check("Has comments", len(items) >= 1, f"got {len(items)} items (replies nest under parent)")

    # ── 15. Comments: Replies endpoint ───────────────────────────
    print("\n15. Comments — Replies (GET /api/v1/comments/:id/replies)")
    if comment_id:
        code, data = _req("GET", f"/api/v1/comments/{comment_id}/replies")
        check("List replies → 200", code == 200, f"got {code}")

    # ── 16. Comments: Like ───────────────────────────────────────
    print("\n16. Comments — Like (POST /api/v1/comments/:id/like)")
    if comment_id:
        code, data = _req("POST", f"/api/v1/comments/{comment_id}/like")
        check("Like comment → 200", code == 200, f"got {code}: {data}")
        check("Comment liked=true", isinstance(data, dict) and data.get("liked") is True)

    # ── 17. Comments: Update ─────────────────────────────────────
    print("\n17. Comments — Update (PATCH /api/v1/comments/:id)")
    if comment_id:
        code, data = _req("PATCH", f"/api/v1/comments/{comment_id}", {"content": "Updated!"})
        check("Update comment → 200", code == 200, f"got {code}: {data}")

    # ── 18. Report Thread ────────────────────────────────────────
    print("\n18. Report — Thread (POST /api/v1/threads/:id/report)")
    if thread_id:
        code, data = _req("POST", f"/api/v1/threads/{thread_id}/report", {
            "reason": "spam",
        })
        check("Report thread → 201", code == 201, f"got {code}: {data}")

    # ── 19. Report Comment ───────────────────────────────────────
    print("\n19. Report — Comment (POST /api/v1/comments/:id/report)")
    if comment_id:
        code, data = _req("POST", f"/api/v1/comments/{comment_id}/report", {
            "reason": "harassment",
        })
        check("Report comment → 201", code == 201, f"got {code}: {data}")

    # ── 20. Notifications ────────────────────────────────────────
    print("\n20. Notifications — List + Unread Count")
    code, data = _req("GET", "/api/v1/notifications?limit=10")
    check("List notifications → 200", code == 200, f"got {code}")

    code, data = _req("GET", "/api/v1/notifications/unread-count")
    check("Unread count → 200", code == 200, f"got {code}")
    check("Has count field", isinstance(data, dict) and "count" in data)

    # Mark all read
    code, data = _req("POST", "/api/v1/notifications/read-all")
    check("Mark all read → 200", code == 200, f"got {code}")

    # ── 21. Search ───────────────────────────────────────────────
    print("\n21. Search — Full-text (GET /api/v1/search/threads)")
    time.sleep(1)  # Let Meilisearch index
    code, data = _req("GET", f"/api/v1/search/threads?q=E2E&limit=10")
    check("Search → 200", code == 200, f"got {code}")
    check("Has items array", isinstance(data, dict) and isinstance(data.get("items"), list))

    # ── 22. Dashboard: My Stats ──────────────────────────────────
    print("\n22. Dashboard — Personal Stats (GET /api/v1/dashboard/me/stats)")
    code, data = _req("GET", "/api/v1/dashboard/me/stats")
    check("My stats → 200", code == 200, f"got {code}: {data}")
    check("Has thread_count", isinstance(data, dict) and "thread_count" in data)

    # ── 23. Dashboard: My Threads ────────────────────────────────
    print("\n23. Dashboard — My Threads (GET /api/v1/dashboard/me/threads)")
    code, data = _req("GET", "/api/v1/dashboard/me/threads?limit=5")
    check("My threads → 200", code == 200, f"got {code}")

    # ── 24. Dashboard: My Comments ───────────────────────────────
    print("\n24. Dashboard — My Comments (GET /api/v1/dashboard/me/comments)")
    code, data = _req("GET", "/api/v1/dashboard/me/comments?limit=5")
    check("My comments → 200", code == 200, f"got {code}")

    # ── 25. Auth: Refresh Token ──────────────────────────────────
    print("\n25. Auth — Refresh Token (POST /api/v1/auth/refresh)")
    # Refresh token is in cookies — gateway injects it into the request body
    code, data = _req("POST", "/api/v1/auth/refresh")
    check("Refresh → 200", code == 200, f"got {code}: {data}")
    check("Response is success message", isinstance(data, dict) and "message" in data, str(data))

    # ── 26. Auth: Change Password ────────────────────────────────
    print("\n26. Auth — Change Password (POST /api/v1/auth/change-password)")
    code, data = _req("POST", "/api/v1/auth/change-password", {
        "current_password": "TestPass123!",
        "new_password": "NewPass456!@",
    })
    check("Change password → 200", code == 200, f"got {code}: {data}")

    # Re-login with new password
    code, data = _req("POST", "/api/v1/auth/login", {"login": username, "password": "NewPass456!@"})
    check("Login with new password → 200", code == 200, f"got {code}")

    # ── 27. Comments: Delete ─────────────────────────────────────
    print("\n27. Comments — Delete (DELETE /api/v1/comments/:id)")
    if reply_id:
        code, data = _req("DELETE", f"/api/v1/comments/{reply_id}")
        check("Delete reply → 200", code == 200, f"got {code}: {data}")

    # ── 28. Threads: Delete ──────────────────────────────────────
    print("\n28. Threads — Delete (DELETE /api/v1/threads/:id)")
    if thread_id:
        code, data = _req("DELETE", f"/api/v1/threads/{thread_id}")
        check("Delete thread → 200", code == 200, f"got {code}: {data}")

    # ── 29. Auth: Logout ─────────────────────────────────────────
    print("\n29. Auth — Logout (POST /api/v1/auth/logout)")
    code, data = _req("POST", "/api/v1/auth/logout")
    check("Logout → 200", code == 200, f"got {code}: {data}")

    # Verify cookies were cleared — refresh should fail
    code2, data2 = _req("POST", "/api/v1/auth/refresh")
    check("Refresh after logout → 401", code2 == 401, f"got {code2}")

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 65)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    print("=" * 65)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
