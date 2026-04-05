"""End-to-end smoke tests for the restructured microservices."""
import http.cookiejar
import json
import random
import sys
import time
import urllib.request

BASE = "http://forum_gateway:8000"
ok = 0
fail = 0

# Cookie jar to capture HttpOnly tokens set by the gateway
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def api(method, path, body=None, headers=None):
    h = headers or {}
    h["Content-Type"] = "application/json"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method=method)
    with opener.open(req, timeout=10) as r:
        return json.loads(r.read())


def check(name, fn):
    global ok, fail
    try:
        result = fn()
        print(f"  PASS  {name}: {result}")
        ok += 1
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        fail += 1


# 1. Login (gateway sets tokens as HttpOnly cookies)
login_resp = api("POST", "/api/v1/auth/login", {"login": "admin", "password": "Admin@1234"})
check("1. Login", lambda: f"message={login_resp['message']}")
# No need for Authorization header — cookies are sent automatically by the opener
h = {}

# 2. Users/me
me = api("GET", "/api/v1/users/me", headers=h)
check("2. Users/me", lambda: f"{me['username']} role={me['role']}")

# 3. Public profile
pub = api("GET", "/api/v1/users/admin")
check("3. Public profile", lambda: f"{pub['username']} role={pub['role']}")

# 4. List threads
tl = api("GET", "/api/v1/threads?limit=3")
check("4. List threads", lambda: f"{len(tl['items'])} items")

# 5. Create thread
nt = api(
    "POST", "/api/v1/threads",
    {"title": f"Smoke {random.randint(0, 99999)}", "description": "Testing restructured services", "tags": ["smoke", "test"]},
    headers=h,
)
check("5. Create thread", lambda: f"tags={nt['tags']}")
thid = nt["id"]

# 6. Get thread
gt = api("GET", f"/api/v1/threads/{thid}")
check("6. Get thread", lambda: f"{gt['title']}")

# 7. Edit thread
et = api("PATCH", f"/api/v1/threads/{thid}", {"title": "Smoke edited"}, headers=h)
check("7. Edit thread", lambda: f"is_edited={et['is_edited']}")

# 8. Comment
cm = api("POST", f"/api/v1/threads/{thid}/comments", {"content": "Test comment"}, headers=h)
check("8. Comment", lambda: f"depth={cm['depth']}")
cmid = cm["id"]

# 9. Reply
rp = api("POST", f"/api/v1/threads/{thid}/comments", {"content": "Reply", "parent_id": cmid}, headers=h)
check("9. Reply", lambda: f"depth={rp['depth']}")

# 10. List comments
lc = api("GET", f"/api/v1/threads/{thid}/comments?limit=10")
check("10. List comments", lambda: f"{len(lc['items'])} items")

# 11. Like thread
lt = api("POST", f"/api/v1/threads/{thid}/like", headers=h)
check("11. Like thread", lambda: f"liked={lt['liked']} count={lt['like_count']}")

# 12. Like status
ls = api("GET", f"/api/v1/threads/{thid}/like/status", headers=h)
check("12. Like status", lambda: f"liked={ls['liked']}")

# 13. Like comment
lk = api("POST", f"/api/v1/comments/{cmid}/like", headers=h)
check("13. Like comment", lambda: f"liked={lk['liked']}")

# 14. Pin
pin = api("POST", f"/api/v1/threads/{thid}/pin", headers=h)
check("14. Pin", lambda: f"is_pinned={pin['is_pinned']}")

# 15. Lock
lock = api("POST", f"/api/v1/threads/{thid}/lock", headers=h)
check("15. Lock", lambda: f"is_locked={lock['is_locked']}")

# 16. Admin users
au = api("GET", "/api/v1/admin/users?limit=3", headers=h)
check("16. Admin users", lambda: f"{len(au['items'])} users")

# 17. Profile threads
pt = api("GET", f"/api/v1/profiles/{me['id']}/threads?limit=3")
check("17. Profile threads", lambda: f"{len(pt['items'])} items")

# 18. Profile stats
ps = api("GET", f"/api/v1/profiles/{me['id']}/stats")
check("18. Profile stats", lambda: f"threads={ps['thread_count']}")

# 19. Notifications
nf = api("GET", "/api/v1/notifications?limit=5", headers=h)
check("19. Notifications", lambda: f"{len(nf['items'])} items")

# 20. Reports
rp2 = api("GET", "/api/v1/reports?limit=5", headers=h)
check("20. Reports", lambda: f"{len(rp2['items'])} items")

# 21. Search (wait for Meilisearch indexing)
time.sleep(2)


def do_search():
    sr = api("GET", "/api/v1/search/threads?q=smoke&limit=3")
    return f"{len(sr['items'])} results"


check("21. Search", do_search)

# 22. Token refresh (refresh_token is in cookie, sent automatically)
ref = api("POST", "/api/v1/auth/refresh")
check("22. Token refresh", lambda: f"message={ref.get('message', ref)}")

# 23. Cleanup: unlock, unpin, delete
api("POST", f"/api/v1/threads/{thid}/lock", headers=h)
api("POST", f"/api/v1/threads/{thid}/pin", headers=h)
dl = api("DELETE", f"/api/v1/threads/{thid}", headers=h)
check("23. Delete thread", lambda: f"{dl['message']}")

print(f"\n=== RESULT: {ok} PASSED, {fail} FAILED ===")
sys.exit(1 if fail else 0)
