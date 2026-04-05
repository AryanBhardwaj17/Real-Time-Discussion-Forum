"""Smoke tests for the microservice stack.

Run from the host machine while docker compose is up:
    python tests/smoke_microservices.py
"""

import sys
import json
import http.cookiejar
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0

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
        with _opener.open(req) as resp:
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
    print("=" * 60)
    print("Microservice Smoke Tests")
    print("=" * 60)

    # ── 1. Gateway health ────────────────────────────────────────
    print("\n1. Gateway Health")
    code, data = _req("GET", "/health")
    check("Gateway /health returns 200", code == 200, f"got {code}")
    check("Response has service=gateway", isinstance(data, dict) and data.get("service") == "gateway", str(data))

    # ── 2. Auth — Register ───────────────────────────────────────
    print("\n2. Auth — Register")
    code, data = _req("POST", "/api/v1/auth/register", {
        "email": "smoke@test.com",
        "username": "smokeuser",
        "password": "Test1234!@#",
    })
    check("Register returns 201 (or 409 if exists)", code in (201, 409), f"got {code}: {data}")
    if code == 201:
        user_id = data.get("id", "") if isinstance(data, dict) else ""
        check("Response has user id", bool(user_id), str(data))
    else:
        check("User already exists (409)", code == 409)

    # ── 3. Auth — Login ──────────────────────────────────────────
    print("\n3. Auth — Login")
    code, data = _req("POST", "/api/v1/auth/login", {
        "login": "smokeuser",
        "password": "Test1234!@#",
    })
    check("Login returns 200", code == 200, f"got {code}: {data}")
    # Tokens are now in HttpOnly cookies, not in the response body
    has_access_cookie = any(c.name == "access_token" for c in _cookie_jar)
    has_refresh_cookie = any(c.name == "refresh_token" for c in _cookie_jar)
    check("Got access_token cookie", has_access_cookie, str([c.name for c in _cookie_jar]))
    check("Got refresh_token cookie", has_refresh_cookie, str([c.name for c in _cookie_jar]))

    # No need for auth headers — cookies are sent automatically

    # ── 4. Auth — Get Profile ────────────────────────────────────
    print("\n4. Auth — Get Profile")
    code, data = _req("GET", "/api/v1/users/me")
    check("GET /users/me returns 200", code == 200, f"got {code}: {data}")
    check("Username matches", isinstance(data, dict) and data.get("username") == "smokeuser", str(data))

    # ── 5. Content — Create Thread ───────────────────────────────
    print("\n5. Content — Create Thread")
    code, data = _req("POST", "/api/v1/threads", {
        "title": "Smoke Test Thread",
        "description": "This is a smoke test thread for the microservice architecture.",
        "tags": ["test", "smoke"],
    })
    check("Create thread returns 201", code == 201, f"got {code}: {data}")
    thread_id = data.get("id", "") if isinstance(data, dict) else ""
    check("Got thread id", bool(thread_id), str(data))

    # ── 6. Content — List Threads ────────────────────────────────
    print("\n6. Content — List Threads")
    code, data = _req("GET", "/api/v1/threads")
    check("List threads returns 200", code == 200, f"got {code}: {data}")
    check("Response has items", isinstance(data, dict) and isinstance(data.get("items"), list), str(data))

    # ── 7. Content — Get Thread ──────────────────────────────────
    print("\n7. Content — Get Thread")
    if thread_id:
        code, data = _req("GET", f"/api/v1/threads/{thread_id}")
        check("Get thread returns 200", code == 200, f"got {code}: {data}")
        check("Title matches", isinstance(data, dict) and data.get("title") == "Smoke Test Thread", str(data))
    else:
        check("Skipped — no thread_id", False, "thread creation failed")

    # ── 8. Content — Create Comment ──────────────────────────────
    print("\n8. Content — Create Comment")
    if thread_id:
        code, data = _req("POST", f"/api/v1/threads/{thread_id}/comments", {
            "content": "This is a smoke test comment.",
        })
        check("Create comment returns 201", code == 201, f"got {code}: {data}")
        comment_id = data.get("id", "") if isinstance(data, dict) else ""
        check("Got comment id", bool(comment_id), str(data))
    else:
        check("Skipped — no thread_id", False, "thread creation failed")
        comment_id = ""

    # ── 9. Content — List Comments ───────────────────────────────
    print("\n9. Content — List Comments")
    if thread_id:
        code, data = _req("GET", f"/api/v1/threads/{thread_id}/comments")
        check("List comments returns 200", code == 200, f"got {code}: {data}")
        check("At least one comment", isinstance(data, dict) and len(data.get("items", [])) >= 1, str(data))

    # ── 10. Content — Like Thread ────────────────────────────────
    print("\n10. Content — Like Thread")
    if thread_id:
        code, data = _req("POST", f"/api/v1/threads/{thread_id}/like")
        check("Like returns 200", code == 200, f"got {code}: {data}")
        check("Liked=true", isinstance(data, dict) and data.get("liked") is True, str(data))

    # ── 11. Notification — List ──────────────────────────────────
    print("\n11. Notifications")
    code, data = _req("GET", "/api/v1/notifications")
    check("List notifications returns 200", code == 200, f"got {code}: {data}")

    code, data = _req("GET", "/api/v1/notifications/unread-count")
    check("Unread count returns 200", code == 200, f"got {code}: {data}")

    # ── 12. Search ───────────────────────────────────────────────
    print("\n12. Search")
    code, data = _req("GET", "/api/v1/search/threads?q=smoke")
    check("Search returns 200", code == 200, f"got {code}: {data}")

    # ── 13. Dashboard — My Stats ─────────────────────────────────
    print("\n13. Dashboard — Personal Stats")
    code, data = _req("GET", "/api/v1/dashboard/me/stats")
    check("My stats returns 200", code == 200, f"got {code}: {data}")

    # ── 14. Auth — Refresh Token ─────────────────────────────────
    print("\n14. Auth — Refresh Token")
    # Refresh token is in cookies — gateway injects it into the request body
    code, data = _req("POST", "/api/v1/auth/refresh")
    check("Refresh returns 200", code == 200, f"got {code}: {data}")
    # New tokens are set as cookies (not in response body)
    check("Response is success message", isinstance(data, dict) and "message" in data, str(data))

    # ── 15. Auth — Logout ────────────────────────────────────────
    print("\n15. Auth — Logout")
    # Logout — refresh token sent via cookie automatically
    code, data = _req("POST", "/api/v1/auth/logout")
    check("Logout returns 200", code == 200, f"got {code}: {data}")

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
