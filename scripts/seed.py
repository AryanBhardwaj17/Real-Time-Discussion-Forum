"""
Seed script for the Real Time Discussion Forum.

Populates the database through the Gateway API so that all side effects
(denormalized usernames, Meilisearch indexing, Redis notifications,
audit events, hot-score calculations) are triggered correctly.

Usage:
    pip install httpx
    python scripts/seed.py                # default: http://localhost:8000
    GATEWAY_URL=http://host:port python scripts/seed.py
"""

from __future__ import annotations

import os
import random
import sys
import time
import httpx

GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")
API = f"{GATEWAY}/api/v1"

# ── Seed Users ────────────────────────────────────────────────────────
ADMIN = {"username": "admin", "password": "Admin@1234"}

USERS = [
    {
        "email": "alice@forum.dev",
        "username": "alice",
        "password": "Alice@1234",
        "name": "Alice Johnson",
    },
    {
        "email": "bob@forum.dev",
        "username": "bob",
        "password": "Bob@12345",
        "name": "Bob Smith",
    },
    {
        "email": "carol@forum.dev",
        "username": "carol",
        "password": "Carol@1234",
        "name": "Carol Williams",
    },
    {
        "email": "dave@forum.dev",
        "username": "dave",
        "password": "Dave@1234",
        "name": "Dave Brown",
    },
    {
        "email": "eve@forum.dev",
        "username": "eve",
        "password": "Eve@12345",
        "name": "Eve Davis",
    },
]

# ── Seed Threads ──────────────────────────────────────────────────────
THREADS = [
    {
        "author": "alice",
        "title": "Getting started with Python asyncio",
        "description": (
            "I've been learning Python for a while and want to dive into async "
            "programming. Can someone explain the difference between `asyncio.run()`, "
            "`asyncio.create_task()`, and `await`? When should I use each one?\n\n"
            "I tried writing a simple web scraper using aiohttp but kept getting "
            "RuntimeError about event loops. Any tips for beginners?"
        ),
        "tags": ["python", "asyncio", "programming"],
    },
    {
        "author": "bob",
        "title": "Best practices for Docker Compose in production",
        "description": (
            "We're currently using Docker Compose for local development, but our team "
            "wants to use it in a staging environment too. What are the best practices?\n\n"
            "Specifically:\n"
            "- How do you handle secrets?\n"
            "- What logging drivers do you recommend?\n"
            "- Should we use `restart: always` or set up a process manager?\n\n"
            "We have about 8 services including PostgreSQL, Redis, and a few FastAPI apps."
        ),
        "tags": ["docker", "devops", "deployment"],
    },
    {
        "author": "carol",
        "title": "React 19 — what's actually new?",
        "description": (
            "React 19 just dropped and I'm trying to understand the key changes. "
            "I've read the blog post but some things are still unclear:\n\n"
            "1. How do Server Components work with existing client-side state management?\n"
            "2. What happened to `forwardRef`?\n"
            "3. Is `use()` hook a replacement for `useEffect` for data fetching?\n\n"
            "Would love to hear from anyone who has migrated a production app."
        ),
        "tags": ["react", "javascript", "frontend"],
    },
    {
        "author": "dave",
        "title": "Understanding database indexing strategies",
        "description": (
            "I have a PostgreSQL table with ~10M rows and queries are getting slow. "
            "Currently I have a B-tree index on the primary key and a few foreign keys.\n\n"
            "Questions:\n"
            "- When should I use a composite index vs separate indexes?\n"
            "- Are partial indexes worth the complexity?\n"
            "- How do GIN indexes compare to GiST for full-text search?\n\n"
            "The table has columns: id, user_id, title, body, tags (array), created_at, "
            "updated_at, status (enum). Most queries filter by user_id + status with "
            "ORDER BY created_at DESC."
        ),
        "tags": ["postgresql", "database", "performance"],
    },
    {
        "author": "eve",
        "title": "Microservices vs Monolith — when to switch?",
        "description": (
            "Our startup has been running a Django monolith for 2 years. We have about "
            "15 developers and the codebase is getting hard to manage. Deploy times are "
            "15 minutes and we're stepping on each other's toes constantly.\n\n"
            "Is it time to move to microservices? What's a good first service to extract? "
            "We're thinking auth or notifications since they have clear boundaries.\n\n"
            "Has anyone gone through this transition? What were the biggest surprises?"
        ),
        "tags": ["architecture", "microservices", "django"],
    },
    {
        "author": "alice",
        "title": "WebSocket authentication patterns",
        "description": (
            "Building a real-time chat app and trying to figure out the best way to "
            "authenticate WebSocket connections. Options I'm considering:\n\n"
            "1. Token in query string: `ws://host/ws?token=xxx`\n"
            "2. Cookie-based (send cookies on upgrade)\n"
            "3. First message authentication\n\n"
            "Option 1 seems easiest but tokens in URLs can leak via logs. "
            "Option 2 only works for same-origin. Option 3 adds complexity.\n\n"
            "What do you all use in production? @bob I saw your Docker post — "
            "do you deploy WebSocket services differently?"
        ),
        "tags": ["websocket", "security", "realtime"],
    },
    {
        "author": "bob",
        "title": "Tailwind CSS vs plain CSS — the great debate",
        "description": (
            "I've been using Tailwind CSS for 6 months now and I have mixed feelings. "
            "The utility-first approach is fast for prototyping but my JSX looks like "
            "alphabet soup.\n\n"
            "Pros I've noticed:\n"
            "- Incredibly fast to prototype\n"
            "- Consistent spacing/color system\n"
            "- Small bundle size with purging\n\n"
            "Cons:\n"
            "- HTML readability suffers\n"
            "- Hard to do complex animations\n"
            "- Team members who know CSS struggle with the mental model shift\n\n"
            "What's your take? @carol you mentioned working with React — what CSS approach do you prefer?"
        ),
        "tags": ["css", "tailwind", "frontend", "react"],
    },
    {
        "author": "carol",
        "title": "Rate limiting strategies for APIs",
        "description": (
            "I'm implementing rate limiting for our public API and need advice on "
            "the algorithm choice.\n\n"
            "**Token Bucket** seems most flexible but requires storing state per client. "
            "**Sliding Window** is simpler but can allow bursts at window boundaries. "
            "**Fixed Window Counter** is easiest but least accurate.\n\n"
            "We're using Redis for state storage. Currently serving ~1000 req/s. "
            "Need to support different limits per endpoint (auth: 10/min, "
            "general: 60/min, search: 30/min).\n\n"
            "Which algorithm do you recommend? Any pitfalls with Redis-based implementations?"
        ),
        "tags": ["api", "ratelimiting", "redis", "backend"],
    },
    {
        "author": "dave",
        "title": "Git workflow for small teams",
        "description": (
            "Our 4-person team is arguing about Git workflow. We've tried:\n\n"
            "1. **GitFlow** — too many branches, overhead for a small team\n"
            "2. **GitHub Flow** — simple but no staging branch\n"
            "3. **Trunk-based** — scary without good CI/CD\n\n"
            "We deploy twice a week and have basic CI (lint + unit tests). "
            "No feature flags yet. What workflow would you recommend?\n\n"
            "@alice @bob — how do your teams handle this?"
        ),
        "tags": ["git", "workflow", "teamwork"],
    },
    {
        "author": "eve",
        "title": "Learning Rust as a Python developer",
        "description": (
            "I've been a Python dev for 5 years and want to learn Rust for systems "
            "programming. The borrow checker is kicking my butt.\n\n"
            "Resources I've tried:\n"
            "- The Rust Book (official) — great but dense\n"
            "- Rustlings exercises — good for syntax\n"
            "- Advent of Code in Rust — fun but I keep fighting lifetimes\n\n"
            "Any tips for making the mental shift from Python's GC model to Rust's "
            "ownership model? What project should I build first?\n\n"
            "Also @dave, PostgreSQL has some Rust extensions now — have you tried any?"
        ),
        "tags": ["rust", "python", "learning", "programming"],
    },
]

# ── Seed Comments ─────────────────────────────────────────────────────
# (thread_index, author, content, parent_comment_key)
# parent_comment_key=None for top-level, otherwise a string key we track
COMMENTS: list[dict] = [
    # Thread 0: asyncio
    {"thread": 0, "author": "bob",   "content": "Great question! The key thing to understand is that `asyncio.run()` creates a new event loop, so you should only call it once at the top level. Inside async functions, use `await` for coroutines and `asyncio.create_task()` when you want concurrent execution.\n\nFor the RuntimeError, make sure you're not calling `asyncio.run()` inside an already running loop (common in Jupyter notebooks).", "parent": None, "key": "c0"},
    {"thread": 0, "author": "carol", "content": "I'd also recommend checking out `anyio` — it's an abstraction layer that works with both asyncio and trio. Makes your code more portable.", "parent": None, "key": "c1"},
    {"thread": 0, "author": "alice", "content": "@bob Thanks! That explains the RuntimeError I was getting. I was calling asyncio.run() inside a FastAPI endpoint which already has a loop running. Switching to `await` fixed it.", "parent": "c0", "key": "c2"},
    {"thread": 0, "author": "dave",  "content": "One thing that tripped me up: `asyncio.gather()` vs `asyncio.create_task()`. `gather` is for when you have a known set of coroutines. `create_task` is better when tasks are created dynamically.", "parent": None, "key": "c3"},
    {"thread": 0, "author": "eve",   "content": "Pro tip: if you're doing web scraping, check out `httpx` with its async client. It's almost a drop-in replacement for `requests` but supports async natively.", "parent": None, "key": "c4"},
    {"thread": 0, "author": "bob",   "content": "@alice Glad it helped! Yeah, FastAPI runs on uvicorn's event loop so you should never create a new one inside it. That's a super common mistake.", "parent": "c2", "key": "c5"},

    # Thread 1: Docker Compose
    {"thread": 1, "author": "alice", "content": "For secrets in Docker Compose, use Docker secrets (with Swarm mode) or environment variable files (.env). Never hardcode secrets in the compose file! We use a `.env.production` that's in .gitignore.", "parent": None, "key": "c6"},
    {"thread": 1, "author": "dave",  "content": "Regarding restart policies — `restart: unless-stopped` is usually better than `always`. With `always`, containers restart even after you manually stop them, which can be annoying during maintenance.", "parent": None, "key": "c7"},
    {"thread": 1, "author": "carol", "content": "For logging, I'd recommend `json-file` driver with max-size and max-file limits. Ship to a central log aggregator (ELK stack or Loki) in production.\n\n```yaml\nlogging:\n  driver: json-file\n  options:\n    max-size: \"10m\"\n    max-file: \"3\"\n```", "parent": None, "key": "c8"},
    {"thread": 1, "author": "bob",   "content": "@alice Good point about .env files! We also use `docker-compose.override.yml` for dev-specific settings so the base compose file stays clean.", "parent": "c6", "key": "c9"},

    # Thread 2: React 19
    {"thread": 2, "author": "alice", "content": "I migrated a medium-sized app (~50k LOC) to React 19 last month. The biggest win is the `use()` hook — it's not exactly a replacement for useEffect, but it makes data fetching way cleaner when combined with Suspense.\n\n`forwardRef` is gone because refs are now just regular props. One less API to remember!", "parent": None, "key": "c10"},
    {"thread": 2, "author": "eve",   "content": "The React Compiler is the real game-changer IMO. No more `useMemo` and `useCallback` everywhere. It automatically memoizes components and values.", "parent": None, "key": "c11"},
    {"thread": 2, "author": "carol", "content": "@alice That's great to hear! Did you face any breaking changes with third-party libraries? I use react-hook-form and react-query extensively.", "parent": "c10", "key": "c12"},
    {"thread": 2, "author": "alice", "content": "@carol react-query (TanStack Query v5) works perfectly. React-hook-form had a minor issue with a deprecated API but they released a patch within a week. Overall smooth migration.", "parent": "c12", "key": "c13"},

    # Thread 3: Database indexing
    {"thread": 3, "author": "bob",   "content": "For your query pattern (user_id + status with ORDER BY created_at DESC), a composite index on `(user_id, status, created_at DESC)` would be ideal. PostgreSQL can use it for both the WHERE and ORDER BY in a single index scan.", "parent": None, "key": "c14"},
    {"thread": 3, "author": "alice", "content": "Partial indexes are absolutely worth it for your case! If most queries filter by `status = 'active'`, create:\n\n```sql\nCREATE INDEX idx_active_posts ON posts (user_id, created_at DESC)\nWHERE status = 'active';\n```\n\nSmaller index = faster lookups + less storage.", "parent": None, "key": "c15"},
    {"thread": 3, "author": "eve",   "content": "For the tags array column, GIN indexes are what you want. GiST is better for geometric/spatial data or range queries. For text search:\n\n- GIN: faster reads, slower writes, larger on disk\n- GiST: balanced read/write, lossy (needs recheck)", "parent": None, "key": "c16"},
    {"thread": 3, "author": "dave",  "content": "@bob That composite index suggestion is perfect. I just tested it and query time went from 450ms to 3ms on my 10M row table. Mind blown.", "parent": "c14", "key": "c17"},
    {"thread": 3, "author": "carol", "content": "Don't forget about `EXPLAIN (ANALYZE, BUFFERS)` — it tells you exactly how PostgreSQL is using your indexes. I often find surprising full-table scans hiding behind what looks like an indexed query.", "parent": None, "key": "c18"},

    # Thread 4: Microservices vs Monolith
    {"thread": 4, "author": "alice", "content": "We went through this exact transition at my last company! Auth was a great first extraction — it has clear inputs/outputs and minimal shared state.\n\nBiggest surprise: you underestimate how much cross-service communication overhead there is. What was a function call becomes an HTTP request with retries, timeouts, and circuit breakers.", "parent": None, "key": "c19"},
    {"thread": 4, "author": "bob",   "content": "I'd actually suggest starting with a \"modular monolith\" first. Enforce clear module boundaries within your Django app (separate Django apps with well-defined interfaces). Then extract to services only when you have a concrete scalability reason.\n\n15 devs is right at the boundary — you might not need microservices yet.", "parent": None, "key": "c20"},
    {"thread": 4, "author": "dave",  "content": "If you do go microservices, invest in observability from day one. Distributed tracing (OpenTelemetry), centralized logging, and service mesh. Without these, debugging production issues in a distributed system is a nightmare.", "parent": None, "key": "c21"},
    {"thread": 4, "author": "eve",   "content": "@alice @bob Both great perspectives! I think we'll try the modular monolith approach first. If we still have issues after 6 months, then we'll extract auth as the first service.", "parent": "c20", "key": "c22"},

    # Thread 5: WebSocket auth
    {"thread": 5, "author": "carol", "content": "We use cookie-based auth for WebSockets in production. Since our frontend and API are same-origin, cookies are sent automatically on the WebSocket upgrade request. The server validates the JWT from the cookie during the handshake.\n\nWorks great and avoids the token-in-URL issue.", "parent": None, "key": "c23"},
    {"thread": 5, "author": "dave",  "content": "For cross-origin scenarios, I've seen a pattern where you:\n1. POST to an endpoint to get a short-lived (30s) connection ticket\n2. Connect with `ws://host/ws?ticket=xxx`\n3. Server validates and invalidates the ticket on first use\n\nAvoids token leaks since the ticket is single-use.", "parent": None, "key": "c24"},
    {"thread": 5, "author": "bob",   "content": "@alice Yeah we deploy WebSocket services on dedicated nodes with sticky sessions. Load balancing WebSockets requires Layer 4 (TCP) balancing — Layer 7 won't work for the persistent connection.", "parent": None, "key": "c25"},

    # Thread 6: Tailwind
    {"thread": 6, "author": "carol", "content": "I've been using Tailwind for about a year now and wouldn't go back. The `@apply` directive helps with readability when classes get too long. For component-heavy React code, I extract common patterns into components rather than fighting with class strings.\n\nFor animations, Tailwind + Framer Motion is a great combo!", "parent": None, "key": "c26"},
    {"thread": 6, "author": "eve",   "content": "Hot take: Tailwind is amazing for solo devs and small teams but becomes harder to maintain in large teams. The lack of semantic class names means you need strong component abstractions to keep things organized.", "parent": None, "key": "c27"},
    {"thread": 6, "author": "alice", "content": "I prefer CSS Modules personally. You get scoped styles without the utility-class bloat. But I admit Tailwind is faster for quick prototypes.\n\nThe real answer is: use whatever your team is productive with. CSS wars are as old as the web itself 😄", "parent": None, "key": "c28"},
    {"thread": 6, "author": "bob",   "content": "@carol @eve Great points from both of you! I think I'll keep Tailwind for now but invest more time in creating reusable components to improve readability.", "parent": "c26", "key": "c29"},

    # Thread 7: Rate limiting
    {"thread": 7, "author": "alice", "content": "Token bucket is the way to go for your use case. Redis makes it easy — store the bucket as a key with TTL, use Lua scripts for atomic refill+consume. Libraries like `redis-cell` provide this out of the box.\n\nFor per-endpoint limits, use a key pattern like `ratelimit:{client_ip}:{endpoint}`.", "parent": None, "key": "c30"},
    {"thread": 7, "author": "dave",  "content": "Watch out for distributed rate limiting gotchas! If you have multiple API servers, make sure they all use the same Redis instance. Also consider what happens when Redis goes down — fail open (allow all) or fail closed (deny all)?", "parent": None, "key": "c31"},
    {"thread": 7, "author": "bob",   "content": "We use sliding window with fixed-point counters in Redis. The approach is:\n1. Key = `{ip}:{endpoint}:{window_seconds}`\n2. INCR the key\n3. EXPIRE if new key\n4. Check count vs limit\n\nSimpler than token bucket and works well for our scale.", "parent": None, "key": "c32"},

    # Thread 8: Git workflow
    {"thread": 8, "author": "carol", "content": "For a 4-person team, GitHub Flow with squash merges is perfect. Keep it simple:\n- `main` is always deployable\n- Feature branches from `main`\n- PR review required before merge\n- Delete branch after merge\n\nAdd a staging branch later when you need it.", "parent": None, "key": "c33"},
    {"thread": 8, "author": "eve",   "content": "Trunk-based isn't scary if you lean into CI/CD. The key is: everyone pushes to main (or very short-lived branches), CI runs on every push, deploy is automated. Feature flags handle incomplete features.\n\nIt forces you to write smaller, more focused commits which is a good habit.", "parent": None, "key": "c34"},
    {"thread": 8, "author": "alice", "content": "@dave Our team (6 people) uses GitHub Flow + environment branches:\n- `main` → production\n- `staging` → staging server (auto-deploy on merge)\n\nPRs target `staging` first, then we promote to `main` after QA. Works great for twice-weekly deploys.", "parent": None, "key": "c35"},
    {"thread": 8, "author": "bob",   "content": "Whatever you choose, invest in `pre-commit` hooks! Linting and formatting on commit prevents a lot of PR noise. We run `ruff`, `mypy`, and `prettier` in hooks — catches 90% of issues before they hit CI.", "parent": None, "key": "c36"},

    # Thread 9: Rust
    {"thread": 9, "author": "carol", "content": "Fellow Python-to-Rust convert here! The trick that made the borrow checker click for me: think of every value as having exactly one owner at a time. References are just temporary loans — the compiler ensures the loan doesn't outlive the owned value.\n\nStart with small CLI tools before attempting anything complex.", "parent": None, "key": "c37"},
    {"thread": 9, "author": "bob",   "content": "Build a tiny HTTP server with `axum` — it's the closest Rust equivalent to FastAPI. You'll learn ownership, trait bounds, and async Rust in a familiar context.\n\nAlso `cargo clippy` is your best friend. It catches non-idiomatic code and suggests improvements.", "parent": None, "key": "c38"},
    {"thread": 9, "author": "dave",  "content": "@eve Yes! `pgx` (now called `pgrx`) lets you write PostgreSQL extensions in Rust. I've been experimenting with it for custom aggregation functions. Performance is insane compared to PL/pgSQL — 50x faster for our use case.", "parent": None, "key": "c39"},
    {"thread": 9, "author": "alice", "content": "One thing that helped me: use `.clone()` liberally at first and don't fight the borrow checker. Once your code works, go back and optimize by removing unnecessary clones. Premature optimization of ownership is the #1 reason Rust beginners give up.", "parent": None, "key": "c40"},
    {"thread": 9, "author": "eve",   "content": "@dave 50x faster?! That's incredible. I'll definitely check out pgrx. @carol @bob Thanks for the tips — I'll start with a CLI tool and work up to axum.", "parent": "c39", "key": "c41"},
]

# ── Likes plan ────────────────────────────────────────────────────────
# (thread_index, liking_user) — skip self-likes
THREAD_LIKES = [
    (0, "bob"), (0, "carol"), (0, "dave"), (0, "eve"),     # asyncio: popular
    (1, "alice"), (1, "dave"), (1, "carol"),                # docker
    (2, "alice"), (2, "bob"), (2, "eve"), (2, "dave"),      # react: popular
    (3, "bob"), (3, "alice"), (3, "eve"),                   # indexing
    (4, "alice"), (4, "bob"), (4, "dave"), (4, "carol"),    # microservices: popular
    (5, "carol"), (5, "dave"), (5, "eve"),                  # websocket
    (6, "carol"), (6, "eve"), (6, "alice"),                 # tailwind
    (7, "alice"), (7, "dave"), (7, "bob"),                  # rate limiting
    (8, "carol"), (8, "eve"),                               # git
    (9, "carol"), (9, "bob"), (9, "alice"), (9, "dave"),    # rust
]

# (comment_key, liking_user)
COMMENT_LIKES = [
    ("c0", "alice"), ("c0", "carol"), ("c0", "dave"),       # bob's asyncio answer
    ("c3", "alice"), ("c3", "bob"),                         # dave's gather tip
    ("c4", "alice"), ("c4", "bob"),                         # eve's httpx tip
    ("c8", "bob"), ("c8", "dave"),                          # carol's logging answer
    ("c10", "carol"), ("c10", "eve"), ("c10", "bob"),       # alice's React migration
    ("c14", "dave"), ("c14", "alice"), ("c14", "eve"),      # bob's index answer
    ("c15", "dave"), ("c15", "bob"),                        # alice's partial index
    ("c19", "eve"), ("c19", "bob"),                         # alice's microservice story
    ("c20", "eve"), ("c20", "alice"), ("c20", "dave"),      # bob's modular monolith
    ("c24", "alice"), ("c24", "bob"),                       # dave's ticket pattern
    ("c37", "eve"), ("c37", "alice"),                       # carol's rust tip
    ("c40", "eve"), ("c40", "carol"),                       # alice's clone tip
]

# ── Reports ───────────────────────────────────────────────────────────
THREAD_REPORTS = [
    # (thread_index, reporter, reason, description)
]

COMMENT_REPORTS = [
    # We'll create some reports from users
    {"comment_key": "c27", "reporter": "bob", "reason": "inappropriate", "description": "Hot takes without nuance are not helpful to the community."},
    {"comment_key": "c28", "reporter": "dave", "reason": "other", "description": "Comment contains an emoji which could be seen as dismissive."},
]

# ── Mod/Admin actions ─────────────────────────────────────────────────
PIN_THREADS = [0, 2]       # Pin asyncio and React threads
LOCK_THREADS = []           # Don't lock anything for testing
EDIT_THREADS = [
    # (thread_index, update_body)
    (1, {"description": (
        "**UPDATED**: We're currently using Docker Compose for local development, "
        "but our team wants to use it in a staging environment too. What are the "
        "best practices?\n\n"
        "Specifically:\n"
        "- How do you handle secrets?\n"
        "- What logging drivers do you recommend?\n"
        "- Should we use `restart: always` or set up a process manager?\n"
        "- **How do you handle health checks effectively?**\n\n"
        "We have about 8 services including PostgreSQL, Redis, and a few FastAPI apps."
    )}),
]
EDIT_COMMENTS = [
    # (comment_key, new_content)
    ("c17", "@bob That composite index suggestion is perfect. I just tested it and query time went from 450ms to 3ms on my 10M row table. Mind blown! **Edit: just ran EXPLAIN ANALYZE and it's doing an Index Only Scan now.**"),
]


# ═══════════════════════════════════════════════════════════════════════
# Bulk Data — enough to trigger pagination across all resources
# ═══════════════════════════════════════════════════════════════════════
#
# Page sizes: threads=20, comments=50, replies=20, notifications=30
# Targets:  ~60 threads (3 pages), ~120 comments on 2 threads (3 pages),
#           ~60+ notifications per user (2 pages)

BULK_THREAD_POOL = [
    ("How to set up CI/CD with GitHub Actions", ["ci-cd", "github", "devops"],
     "I want to automate our deployment pipeline using GitHub Actions. We have a Python FastAPI backend and a React frontend deployed to AWS ECS. What's the best way to structure the workflow files? Should I use a monorepo action or separate workflows per service?"),
    ("Understanding OAuth 2.0 and OpenID Connect", ["security", "oauth", "authentication"],
     "Can someone break down the difference between OAuth 2.0 and OIDC? I keep confusing authorization vs authentication. When should I use the authorization code flow vs the implicit flow? We're building a B2B SaaS product and need to support SSO with Google and Microsoft."),
    ("PostgreSQL vs MySQL in 2026", ["database", "postgresql", "mysql"],
     "We're choosing a relational database for a new project. Our team has experience with both PostgreSQL and MySQL. What are the current advantages of each in 2026? I've heard PostgreSQL is better for complex queries and JSON support, but MySQL has better replication."),
    ("How to handle file uploads in a microservice architecture", ["architecture", "file-upload", "s3"],
     "We need to support large file uploads (up to 500MB) in our microservice stack. Should the API gateway handle the upload and stream to an object store, or should the client upload directly to S3 with presigned URLs? What about virus scanning and validation?"),
    ("Python type hints — are they worth the effort?", ["python", "typing", "best-practices"],
     "Our codebase is 80% untyped Python. The team is debating whether to invest time adding type hints everywhere. We've tried mypy in strict mode on a few modules and it caught some bugs, but it also slowed us down significantly. What's your experience?"),
    ("Designing a notification system at scale", ["system-design", "notifications", "architecture"],
     "We're redesigning our notification system to handle millions of users. Currently it's a simple polling endpoint, but we need to support: push notifications, email digests, in-app real-time, and SMS for critical alerts. Looking for architecture advice."),
    ("Kubernetes vs Docker Swarm for small teams", ["kubernetes", "docker", "infrastructure"],
     "Our 5-person team currently uses Docker Compose in production (yes, really). We want to move to a proper orchestrator but Kubernetes seems like massive overkill. Has anyone used Docker Swarm or Nomad successfully for a similar team size?"),
    ("GraphQL vs REST — lessons learned after 3 years", ["graphql", "rest", "api"],
     "We switched from REST to GraphQL 3 years ago for our primary API. Here are my honest thoughts: the DX was amazing at first, but N+1 queries, caching complexity, and authorization at the resolver level became real pain points. Thinking about switching back."),
    ("How to do database migrations safely in production", ["database", "migrations", "devops"],
     "Our last Alembic migration took down production for 20 minutes because it locked a 50M-row table. What strategies do you use for safe production migrations? We've heard about expand-and-contract, online schema changes, and blue-green deployments."),
    ("Building a real-time collaborative editor", ["realtime", "collaboration", "websocket"],
     "I want to build a Google Docs-like collaborative editor. The two main approaches seem to be OT (Operational Transform) and CRDT (Conflict-free Replicated Data Types). CRDTs seem simpler conceptually but the implementations I've seen are complex. Any recommendations?"),
    ("Best logging practices for microservices", ["logging", "observability", "microservices"],
     "With 12 microservices in production, our logging is a mess. Different formats, no correlation IDs, and searching Kibana takes forever. What logging standards should we adopt? Structured JSON? OpenTelemetry? How do you handle log levels across services?"),
    ("How to write effective code reviews", ["code-review", "teamwork", "best-practices"],
     "I've been doing code reviews for 5 years and I've noticed patterns in what makes reviews effective vs counterproductive. Interested in hearing from others: How many LOC is too many for a single PR? How do you balance speed with thoroughness?"),
    ("Redis Streams vs Kafka for event-driven architecture", ["redis", "kafka", "event-driven"],
     "We're choosing between Redis Streams and Kafka for our event-driven architecture. Our throughput is moderate (~10K events/sec) but we need guaranteed delivery, consumer groups, and at-least-once semantics. Redis Streams seems simpler but is it reliable enough?"),
    ("Optimizing React rendering performance", ["react", "performance", "frontend"],
     "Our React app has become sluggish — the main dashboard takes 3.5 seconds to become interactive. React DevTools shows hundreds of unnecessary re-renders on state changes. We've tried useMemo and useCallback but they feel like band-aids. What's the systematic approach?"),
    ("Introduction to WebAssembly for web developers", ["webassembly", "wasm", "performance"],
     "I keep hearing about WebAssembly but I'm not sure when it's worth using. When does it make sense to write WASM instead of JavaScript? I've seen demos of Photoshop and Figma using it, but for typical web apps, is the complexity justified?"),
    ("How to handle authentication in SPAs", ["security", "spa", "authentication"],
     "We're debating cookie-based vs token-based auth for our React SPA. HttpOnly cookies seem more secure (no XSS risk for tokens) but complicate CORS for cross-domain setups. What's the current best practice? We previously used localStorage which I know is bad."),
    ("Effective error handling patterns in Python", ["python", "error-handling", "best-practices"],
     "I see wildly different approaches to error handling in Python codebases. Some use exceptions for everything, others return Result types, and some use error codes. What patterns have worked best for you in large-scale applications?"),
    ("Setting up a monorepo with Turborepo", ["monorepo", "turborepo", "tooling"],
     "We're consolidating our 6 separate repos into a monorepo. Turborepo, Nx, and Bazel are the main options. We have 3 TypeScript services, 1 Python backend, and 2 React apps. Anyone have experience with Turborepo specifically for mixed-language projects?"),
    ("Understanding CAP theorem with real examples", ["distributed-systems", "database", "theory"],
     "I've read about CAP theorem many times but always found it abstract. Can someone explain it with concrete examples? Like, what does it mean for DynamoDB vs PostgreSQL vs Cassandra in practice? How do you choose between consistency and availability for different use cases?"),
    ("Building a CLI tool in Go vs Rust", ["go", "rust", "cli"],
     "I want to build a cross-platform CLI tool for managing our infrastructure. Both Go and Rust produce static binaries with no runtime dependencies. Go seems simpler to learn, Rust seems faster. The tool will need HTTP client, JSON parsing, and SSH tunneling. What would you choose?"),
    ("How to test microservices effectively", ["testing", "microservices", "best-practices"],
     "Unit tests are straightforward, but how do you test the interactions between microservices? We have contract tests with Pact, but they miss a lot of integration issues. Full end-to-end tests are slow and flaky. What's the right balance?"),
    ("Modern CSS — is Flexbox enough or do I need Grid?", ["css", "flexbox", "grid"],
     "I've been using Flexbox for everything and it works well for most layouts. When is CSS Grid actually necessary? I've heard Grid is for 2D layouts and Flexbox for 1D, but in practice, I can usually nest Flexbox containers to achieve 2D layouts too."),
    ("Deploying Python apps — uv vs pip vs poetry", ["python", "packaging", "tooling"],
     "The Python packaging ecosystem in 2026 is overwhelming. We have pip, poetry, pdm, hatch, and now uv which claims to be 10-100x faster. What's the current recommended approach for a production FastAPI application? We need reproducible builds and fast CI installs."),
    ("Implementing full-text search — Elasticsearch vs Meilisearch vs Typesense", ["search", "elasticsearch", "meilisearch"],
     "We need to add search to our product catalog (~500K items). Elasticsearch is the standard but seems heavyweight. Meilisearch and Typesense are simpler but how do they handle complex queries, faceting, and geo-search? We need sub-100ms latency."),
    ("Understanding connection pooling in PostgreSQL", ["postgresql", "performance", "database"],
     "Our app occasionally throws 'too many connections' errors under load. We use SQLAlchemy with asyncpg and have pool_size=20. Should we use PgBouncer? What's the difference between session pooling and transaction pooling? We have about 1000 req/sec."),
    ("How to structure a large React application", ["react", "architecture", "frontend"],
     "Our React app has grown to 200+ components and it's getting hard to navigate. We're using a flat structure but thinking about feature-based folders. What's worked for large teams? Also, should we split into micro-frontends or is that overkill?"),
    ("Caching strategies — when to use Redis vs CDN vs browser cache", ["caching", "redis", "performance"],
     "We have different caching needs across our stack: API response caching, session storage, database query caching, and static asset caching. Using Redis for everything seems wasteful. How do you decide which caching layer to use for what?"),
    ("Securing Docker containers in production", ["docker", "security", "devops"],
     "We run 15 Docker containers in production and I want to audit our security posture. What are the must-have security practices? I know about running as non-root, scanning images, and read-only filesystems, but what else am I missing?"),
    ("Event sourcing — is it worth the complexity?", ["architecture", "event-sourcing", "cqrs"],
     "Our team is considering event sourcing for our financial transaction system. The benefits of complete audit trail and time-travel queries are appealing, but I'm worried about complexity: projection rebuilding, eventual consistency, and the learning curve. Has anyone regretted adopting event sourcing?"),
    ("How to do API versioning right", ["api", "versioning", "best-practices"],
     "Our public API has been live for 2 years and we need to make breaking changes. Should we use URL versioning (/v2/), header versioning, or query parameter versioning? What strategies exist for supporting old versions while migrating clients?"),
    ("Understanding DNS from a developer's perspective", ["networking", "dns", "infrastructure"],
     "I realized I don't really understand DNS beyond 'it translates domain names to IPs.' How does caching work at each layer? What's the difference between A, CNAME, AAAA, MX, and TXT records? How does DNS failover work for high availability?"),
    ("Python async pitfalls — what they don't tell you", ["python", "asyncio", "gotchas"],
     "After 2 years of production async Python with FastAPI, here are the pitfalls that caught us off guard: CPU-bound work blocking the event loop, difficult debugging with stack traces, SQLAlchemy async gotchas, and the sync-to-async boundary issues. Anyone else relate?"),
    ("How to choose between SOA and microservices", ["architecture", "microservices", "soa"],
     "Our company keeps using 'microservices' and 'SOA' interchangeably, but they're not the same thing. We have 8 services communicating via REST and RabbitMQ. Is that microservices or SOA? Does the distinction even matter in practice?"),
    ("Load testing your API — tools and methodology", ["testing", "performance", "api"],
     "We need to load test our API before a big product launch. Comparing tools: k6 (JS-based, modern), Locust (Python-based, simple), Gatling (Scala, powerful), and Apache JMeter (old but battle-tested). Which one do you recommend for testing a REST + WebSocket API?"),
    ("Implementing rate limiting with Redis", ["redis", "rate-limiting", "backend"],
     "I'm implementing rate limiting for our API and want to use Redis for the state store. The main algorithms I'm considering are fixed window, sliding window log, sliding window counter, and token bucket. Which approach gives the best balance of accuracy vs Redis memory usage?"),
    ("Database sharding — when and how", ["database", "sharding", "scalability"],
     "Our main PostgreSQL database is approaching 2TB and query performance is degrading. We're considering sharding by tenant_id since we're a multi-tenant SaaS. What's the practical guide to implementing horizontal sharding? Should we use Citus or roll our own?"),
    ("Managing secrets in a microservice environment", ["security", "secrets", "devops"],
     "Currently we pass secrets as environment variables in docker-compose (yes, I know). For production we need something better. Comparing: HashiCorp Vault, AWS Secrets Manager, Docker secrets, and sealed-secrets for K8s. What's the pragmatic choice for a small team?"),
    ("Understanding React Server Components", ["react", "rsc", "frontend"],
     "I've been reading about React Server Components but I'm still confused about the mental model. When should a component be a server component vs client component? How does state work across the boundary? Does this make React more like PHP?"),
    ("Profiling Python applications — finding bottlenecks", ["python", "performance", "profiling"],
     "Our FastAPI app handles requests in 200ms on average but we have p99 spikes to 2 seconds. What profiling tools do you use for async Python? I've tried cProfile but it doesn't work well with asyncio. py-spy looks promising but I haven't tried it in production."),
    ("gRPC vs REST for internal microservice communication", ["grpc", "rest", "microservices"],
     "All our inter-service calls are REST/JSON but we're hitting performance issues with large payloads. gRPC with protobuf would be faster, but it adds complexity: code generation, .proto file management, and debugging is harder. Is the performance gain worth it?"),
    ("How to build a feature flag system", ["feature-flags", "devops", "deployment"],
     "We want to implement feature flags to enable trunk-based development. Debating between building a simple in-house system (Redis-backed) vs using LaunchDarkly or Unleash. For a team of 10 devs with ~20 active flags, what's the right level of investment?"),
    ("Terraform vs Pulumi for infrastructure as code", ["terraform", "pulumi", "iac"],
     "We're adopting IaC and need to choose between Terraform (HCL) and Pulumi (real programming languages). Terraform has a bigger ecosystem and more examples online, but Pulumi lets us use Python which our team already knows. Any gotchas with either?"),
    ("Browser DevTools tips that saved me hours", ["debugging", "devtools", "frontend"],
     "Sharing some Chrome DevTools features that blew my mind: conditional breakpoints with console.log, the Performance panel's flame chart, Network throttling for testing slow connections, and $0 to reference the currently selected element. What are your favorite hidden features?"),
    ("Understanding memory management in Python", ["python", "memory", "performance"],
     "Our Python service has a memory leak — RSS grows from 200MB to 2GB over 24 hours. I know Python uses reference counting + garbage collection, but how do I find the leak? tracemalloc, objgraph, and pympler are tools I've heard of but never used."),
    ("Writing maintainable SQL queries", ["sql", "database", "best-practices"],
     "Our codebase has SQL queries that are 200+ lines long with multiple CTEs, window functions, and subqueries. They work but nobody can understand them 6 months later. What are your strategies for writing complex SQL that's still readable and maintainable?"),
    ("Migrating from JavaScript to TypeScript incrementally", ["typescript", "javascript", "migration"],
     "We have a 100K LOC JavaScript React app and want to migrate to TypeScript. Going all-in at once isn't feasible. What's the best incremental strategy? Do we start with strict mode everywhere or use 'any' liberally and tighten later?"),
    ("Understanding CORS — once and for all", ["cors", "security", "web"],
     "I've fixed CORS errors hundreds of times but I still don't fully understand why they happen. Can someone explain: Why does the browser send a preflight OPTIONS request? Why do cookies need specific CORS headers? What's the difference between simple and preflighted requests?"),
    ("How to document APIs effectively", ["api", "documentation", "best-practices"],
     "Our API docs are auto-generated from OpenAPI but they're not helpful. They list every endpoint but don't explain workflows, common patterns, or error handling. What makes great API documentation? I'm looking at Stripe and Twilio as inspiration."),
    ("Comparing message queues — RabbitMQ vs SQS vs Redis pub/sub", ["messaging", "rabbitmq", "architecture"],
     "We need a message queue for async job processing. Requirements: ~5K messages/sec, at-least-once delivery, dead letter queues, and monitoring. RabbitMQ is the classic choice, SQS is managed, Redis we already have. How do you decide?"),
    ("Understanding HTTP/2 and HTTP/3", ["http", "networking", "performance"],
     "I'm optimizing our API's network performance and realized we're still on HTTP/1.1. What practical benefits would HTTP/2 bring for our API? Header compression, multiplexing, and server push sound great but are they meaningful for a REST API behind nginx?"),
    ("Zero-downtime deployments — a practical guide", ["deployment", "devops", "availability"],
     "We currently have 30 seconds of downtime per deployment. I want to achieve zero-downtime using rolling deployments or blue-green. We use Docker Compose with nginx as the reverse proxy. What's the simplest path to zero-downtime without Kubernetes?"),
]

BULK_COMMENT_TEMPLATES = [
    "Great question! In my experience, {topic} really depends on the scale of your project. For smaller teams, simpler solutions work better.",
    "I've been dealing with this exact issue at work. We ended up going with the first option and it's been working well for 6 months now.",
    "Thanks for sharing this! One thing I'd add: make sure you benchmark your specific use case before committing to any approach.",
    "This is a really thoughtful analysis. The part about {topic} resonated with me — we hit the same wall last year.",
    "@{mention} I agree with your point. We tried something similar and the results were promising. Would recommend starting small.",
    "Strongly disagree with the premise here. {topic} has evolved significantly and the old advice doesn't apply anymore.",
    "Has anyone tried the new approach that was announced at the last conference? It seems to solve most of these issues elegantly.",
    "I wrote a blog post about this last month if anyone's interested. The key insight was that you don't need to solve everything at once.",
    "One gotcha that nobody mentions: when you scale past a certain point, all the simple solutions break. Plan for that from the start.",
    "This is exactly what we discussed in our architecture review. The consensus was to start with the simplest approach and iterate.",
    "Nice thread! Bookmarking for our next sprint planning. @{mention} you might find this useful for that project you mentioned.",
    "Here's what worked for us in production: start with the defaults, measure everything, then optimize only what matters.",
    "I've tried 3 different approaches to this over the past 2 years. Here's my ranking from best to worst...",
    "Pro tip: don't over-engineer this from the start. Our first version was a simple script and it handled 10x what we expected.",
    "This reminds me of a great talk from PyCon last year. The speaker showed benchmarks comparing all the popular approaches.",
    "We migrated to this approach last quarter and our reliability went from 99.5% to 99.99%. Huge win for relatively little effort.",
    "Important caveat: this advice applies mostly to greenfield projects. If you have existing infrastructure, the calculus changes.",
    "+1 on this. We had the same problem and the solution was simpler than expected once we understood the root cause.",
    "Interesting perspective. I'd add that team expertise should be a major factor in these decisions, not just technical merits.",
    "We spent 3 months evaluating different options for this and ended up going with the most boring, well-tested solution. No regrets.",
]


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

class SessionStore:
    """Maintains per-user httpx clients with cookie jars."""

    def __init__(self):
        self._clients: dict[str, httpx.Client] = {}

    def get(self, username: str) -> httpx.Client:
        if username not in self._clients:
            self._clients[username] = httpx.Client(base_url=API, timeout=30)
        return self._clients[username]

    def close_all(self):
        for c in self._clients.values():
            c.close()


store = SessionStore()

# Maps: username -> user_id, thread_index -> thread_id, comment_key -> comment_id
user_ids: dict[str, str] = {}
thread_ids: dict[int, str] = {}
comment_ids: dict[str, str] = {}

# Indices of threads that already existed in the DB (populated by discover_existing_data)
existing_thread_indices: set[int] = set()


def _check(resp: httpx.Response, label: str):
    if resp.status_code >= 400:
        print(f"  ✗ {label}: {resp.status_code} — {resp.text[:300]}")
        return False
    return True


def step(msg: str):
    print(f"\n{'─'*60}\n  ▶ {msg}\n{'─'*60}")


# ═══════════════════════════════════════════════════════════════════════
# Discovery (idempotency)
# ═══════════════════════════════════════════════════════════════════════

def discover_existing_data():
    """Fetch existing threads/comments to avoid duplicates on re-run."""
    step("Discovering existing data")
    client = store.get("admin")

    # Fetch all threads (paginated) and build title → data map
    all_threads: list[dict] = []
    cursor = None
    while True:
        params: dict = {"sort": "new", "limit": 20}
        if cursor:
            params["cursor"] = cursor
        resp = client.get("/threads", params=params)
        if not _check(resp, "discover threads"):
            break
        body = resp.json()
        all_threads.extend(body.get("items", []))
        if not body.get("has_more"):
            break
        cursor = body.get("next_cursor")

    title_map: dict[str, dict] = {}
    for t in all_threads:
        title_map[t["title"]] = t

    found_threads = 0

    # Match handcrafted threads
    for i, t in enumerate(THREADS):
        if t["title"] in title_map:
            thread_ids[i] = title_map[t["title"]]["id"]
            existing_thread_indices.add(i)
            found_threads += 1

    # Match bulk threads
    for i, (title, _, _) in enumerate(BULK_THREAD_POOL):
        if title in title_map:
            idx = len(THREADS) + i
            thread_ids[idx] = title_map[title]["id"]
            existing_thread_indices.add(idx)
            found_threads += 1

    print(f"  ✓ Found {found_threads} existing threads")

    # Discover comments for existing handcrafted threads
    if existing_thread_indices:
        _discover_comments(client)


def _discover_comments(client: httpx.Client):
    """Fetch comments from existing threads to populate comment_ids for edits/reports."""
    found = 0
    for i in range(len(THREADS)):
        if i not in existing_thread_indices:
            continue
        tid = thread_ids.get(i)
        if not tid:
            continue

        # Fetch all comments for this thread
        all_comments: list[dict] = []
        cursor = None
        while True:
            params: dict = {"sort": "old", "limit": 50}
            if cursor:
                params["cursor"] = cursor
            resp = client.get(f"/threads/{tid}/comments", params=params)
            if not _check(resp, f"discover comments thread {i}"):
                break
            body = resp.json()
            all_comments.extend(body.get("items", []))
            if not body.get("has_more"):
                break
            cursor = body.get("next_cursor")

        # Match seed comments by author + content prefix
        for c in COMMENTS:
            if c["thread"] != i:
                continue
            for existing in all_comments:
                if (existing["author_username"] == c["author"]
                        and existing["content"][:80] == c["content"][:80]):
                    comment_ids[c["key"]] = existing["id"]
                    found += 1
                    break

    print(f"  ✓ Matched {found} existing comments")


# ═══════════════════════════════════════════════════════════════════════
# Seed Steps
# ═══════════════════════════════════════════════════════════════════════

def register_users():
    step("Registering users")
    for u in USERS:
        client = store.get(u["username"])
        resp = client.post("/auth/register", json=u)
        if resp.status_code == 409:
            print(f"  • {u['username']} already exists, logging in...")
        elif not _check(resp, f"register {u['username']}"):
            continue
        else:
            data = resp.json()
            user_ids[u["username"]] = data["id"]
            print(f"  ✓ Registered {u['username']} ({data['id'][:8]}...)")
        # Log in to obtain cookies
        login_resp = client.post("/auth/login", json={
            "login": u["username"],
            "password": u["password"],
        })
        if _check(login_resp, f"login {u['username']}"):
            body = login_resp.json()
            if u["username"] not in user_ids:
                # Get user ID from /users/me
                me = client.get("/users/me")
                if _check(me, f"me {u['username']}"):
                    user_ids[u["username"]] = me.json()["id"]
            print(f"  ✓ Logged in as {u['username']}")


def login_admin():
    step("Logging in as admin")
    client = store.get("admin")
    resp = client.post("/auth/login", json={"login": ADMIN["username"], "password": ADMIN["password"]})
    if _check(resp, "admin login"):
        me = client.get("/users/me")
        if _check(me, "admin me"):
            user_ids["admin"] = me.json()["id"]
            print(f"  ✓ Logged in as admin ({user_ids['admin'][:8]}...)")


def promote_moderator():
    step("Promoting alice to moderator")
    client = store.get("admin")
    uid = user_ids.get("alice")
    if not uid:
        print("  ✗ alice user_id not found, skipping")
        return
    resp = client.patch(f"/admin/users/{uid}/role", json={"role": "moderator"})
    if _check(resp, "promote alice"):
        print(f"  ✓ alice is now moderator")


def update_profiles():
    step("Updating user profiles")
    profiles = {
        "alice": {"bio": "Full-stack developer | Python & React | Previously at Stripe | Open source enthusiast"},
        "bob": {"bio": "DevOps engineer at heart, developer by trade. Docker, Kubernetes, CI/CD."},
        "carol": {"bio": "Frontend architect | React, TypeScript, and all things web. Writing clean UIs since 2015."},
        "dave": {"bio": "Database engineer & PostgreSQL advocate. If your queries are slow, I can help."},
        "eve": {"bio": "Startup CTO | Building things from 0 to 1. Currently exploring Rust and systems programming."},
    }
    for username, update in profiles.items():
        client = store.get(username)
        resp = client.patch("/users/me", json=update)
        if _check(resp, f"profile {username}"):
            print(f"  ✓ Updated profile for {username}")


def create_threads():
    step("Creating threads")
    created, skipped = 0, 0
    for i, t in enumerate(THREADS):
        if i in existing_thread_indices:
            print(f"  • [{i}] \"{t['title'][:50]}\" already exists, skipping")
            skipped += 1
            continue
        client = store.get(t["author"])
        body = {"title": t["title"], "description": t["description"]}
        if t.get("tags"):
            body["tags"] = t["tags"]
        resp = client.post("/threads", json=body)
        if _check(resp, f"thread {i}"):
            data = resp.json()
            thread_ids[i] = data["id"]
            created += 1
            print(f"  ✓ [{i}] \"{t['title'][:50]}\" by {t['author']}")
        time.sleep(0.3)  # small delay so created_at ordering is meaningful
    print(f"  ✓ Created {created}, skipped {skipped} existing")


def create_comments():
    step("Creating comments")
    created, skipped = 0, 0
    for c in COMMENTS:
        ti = c["thread"]
        tid = thread_ids.get(ti)
        if not tid:
            print(f"  ✗ Thread {ti} not found, skipping comment")
            continue
        # Skip if this comment was already discovered in the DB
        if c["key"] in comment_ids:
            skipped += 1
            continue
        client = store.get(c["author"])
        body: dict = {"content": c["content"]}
        if c["parent"]:
            parent_id = comment_ids.get(c["parent"])
            if not parent_id:
                print(f"  ✗ Parent {c['parent']} not found, posting as top-level")
            else:
                body["parent_id"] = parent_id
        resp = client.post(f"/threads/{tid}/comments", json=body)
        if _check(resp, f"comment {c['key']}"):
            data = resp.json()
            comment_ids[c["key"]] = data["id"]
            parent_label = f" (reply to {c['parent']})" if c["parent"] else ""
            print(f"  ✓ {c['key']}: {c['author']} on thread {ti}{parent_label}")
            created += 1
        time.sleep(0.15)
    print(f"  ✓ Created {created} comments, skipped {skipped} existing")


def like_threads():
    step("Liking threads")
    liked, skipped = 0, 0
    for ti, user in THREAD_LIKES:
        tid = thread_ids.get(ti)
        if not tid:
            continue
        client = store.get(user)
        # Check if already liked
        status = client.get(f"/threads/{tid}/like/status")
        if status.status_code == 200 and status.json().get("liked"):
            skipped += 1
            continue
        resp = client.post(f"/threads/{tid}/like")
        if _check(resp, f"like thread {ti} by {user}"):
            data = resp.json()
            liked += 1
            print(f"  ✓ {user} liked thread {ti} (count: {data.get('like_count', '?')})")
        time.sleep(0.1)
    print(f"  ✓ Liked {liked} threads, skipped {skipped} already liked")


def like_comments():
    step("Liking comments")
    liked, skipped = 0, 0
    for ckey, user in COMMENT_LIKES:
        cid = comment_ids.get(ckey)
        if not cid:
            continue
        client = store.get(user)
        # Check if already liked
        status = client.get(f"/comments/{cid}/like/status")
        if status.status_code == 200 and status.json().get("liked"):
            skipped += 1
            continue
        resp = client.post(f"/comments/{cid}/like")
        if _check(resp, f"like {ckey} by {user}"):
            data = resp.json()
            liked += 1
            print(f"  ✓ {user} liked {ckey} (count: {data.get('like_count', '?')})")
        time.sleep(0.1)
    print(f"  ✓ Liked {liked} comments, skipped {skipped} already liked")


def edit_content():
    step("Editing threads and comments")
    for ti, update_body in EDIT_THREADS:
        tid = thread_ids.get(ti)
        if not tid:
            continue
        author = THREADS[ti]["author"]
        client = store.get(author)
        resp = client.patch(f"/threads/{tid}", json=update_body)
        if _check(resp, f"edit thread {ti}"):
            print(f"  ✓ Edited thread {ti} by {author}")

    for ckey, new_content in EDIT_COMMENTS:
        cid = comment_ids.get(ckey)
        if not cid:
            continue
        # Find the author of this comment
        author = next(c["author"] for c in COMMENTS if c["key"] == ckey)
        client = store.get(author)
        resp = client.patch(f"/comments/{cid}", json={"content": new_content})
        if _check(resp, f"edit comment {ckey}"):
            print(f"  ✓ Edited comment {ckey} by {author}")


def report_content():
    step("Creating reports")
    for r in COMMENT_REPORTS:
        cid = comment_ids.get(r["comment_key"])
        if not cid:
            continue
        client = store.get(r["reporter"])
        body = {"reason": r["reason"]}
        if r.get("description"):
            body["description"] = r["description"]
        resp = client.post(f"/comments/{cid}/report", json=body)
        if resp.status_code == 409:
            print(f"  • {r['reporter']} already reported {r['comment_key']}, skipping")
        elif _check(resp, f"report {r['comment_key']}"):
            print(f"  ✓ {r['reporter']} reported comment {r['comment_key']} ({r['reason']})")


def pin_threads():
    step("Pinning threads (as moderator alice)")
    # Re-login alice to get fresh token with moderator role
    client = store.get("alice")
    client.post("/auth/login", json={
        "login": "alice",
        "password": "Alice@1234",
    })
    pinned, skipped = 0, 0
    for ti in PIN_THREADS:
        tid = thread_ids.get(ti)
        if not tid:
            continue
        # Check if already pinned
        detail = client.get(f"/threads/{tid}")
        if detail.status_code == 200 and detail.json().get("is_pinned"):
            print(f"  • Thread {ti} already pinned, skipping")
            skipped += 1
            continue
        resp = client.post(f"/threads/{tid}/pin")
        if _check(resp, f"pin thread {ti}"):
            pinned += 1
            print(f"  ✓ Pinned thread {ti}: \"{THREADS[ti]['title'][:40]}\"")
    print(f"  ✓ Pinned {pinned}, skipped {skipped} already pinned")


# ── Bulk generation (for pagination testing) ─────────────────────────

_all_regular_users = ["alice", "bob", "carol", "dave", "eve"]


def create_bulk_threads():
    """Create 50 additional threads to push total past 3 pages (60+)."""
    step(f"Creating {len(BULK_THREAD_POOL)} bulk threads for pagination")
    random.seed(42)  # deterministic
    created, skipped = 0, 0
    for i, (title, tags, desc) in enumerate(BULK_THREAD_POOL):
        idx = len(THREADS) + i  # offset past handcrafted threads
        if idx in existing_thread_indices:
            skipped += 1
            continue
        author = _all_regular_users[i % len(_all_regular_users)]
        client = store.get(author)
        body = {"title": title, "description": desc, "tags": tags}
        resp = client.post("/threads", json=body)
        if _check(resp, f"bulk thread {idx}"):
            thread_ids[idx] = resp.json()["id"]
            created += 1
        time.sleep(0.15)
    print(f"  ✓ Created {created}, skipped {skipped} existing (total: {len(thread_ids)})")


def create_bulk_comments():
    """Add ~120 comments spread across threads to push popular ones past 50."""
    step("Creating bulk comments for pagination")
    random.seed(123)
    ok, skipped_threads = 0, 0

    # Pick 3 popular handcrafted threads to load with 55+ comments each
    heavy_threads = [0, 3, 4]  # asyncio, indexing, microservices

    for ti in heavy_threads:
        tid = thread_ids.get(ti)
        if not tid:
            continue
        # Skip if thread already had bulk comments from a previous run
        if ti in existing_thread_indices:
            print(f"  • Thread {ti}: already exists, skipping bulk comments")
            skipped_threads += 1
            continue
        for j in range(55):
            author = _all_regular_users[j % len(_all_regular_users)]
            # Pick a different user for mentions
            mention = _all_regular_users[(j + 2) % len(_all_regular_users)]
            topic = THREADS[ti]["title"].split("—")[0].split("?")[0].strip()[:30]
            template = BULK_COMMENT_TEMPLATES[j % len(BULK_COMMENT_TEMPLATES)]
            content = template.format(topic=topic, mention=mention)
            client = store.get(author)
            resp = client.post(f"/threads/{tid}/comments", json={"content": content})
            if resp.status_code < 400:
                ok += 1
            time.sleep(0.05)
        print(f"  ✓ Thread {ti}: added 55 comments")

    # Also spread ~10 comments on each of the first 20 bulk threads
    for bi in range(20):
        idx = len(THREADS) + bi
        tid = thread_ids.get(idx)
        if not tid:
            continue
        # Skip if this bulk thread already existed
        if idx in existing_thread_indices:
            skipped_threads += 1
            continue
        for j in range(10):
            author = _all_regular_users[(bi + j) % len(_all_regular_users)]
            mention = _all_regular_users[(bi + j + 1) % len(_all_regular_users)]
            template = BULK_COMMENT_TEMPLATES[(bi + j) % len(BULK_COMMENT_TEMPLATES)]
            content = template.format(
                topic=BULK_THREAD_POOL[bi][0][:25],
                mention=mention,
            )
            client = store.get(author)
            resp = client.post(f"/threads/{tid}/comments", json={"content": content})
            if resp.status_code < 400:
                ok += 1
            time.sleep(0.05)

    print(f"  ✓ Created {ok} bulk comments (skipped {skipped_threads} existing threads)")


def bulk_likes():
    """Like bulk threads + heavy-comment threads so notifications exceed 30."""
    step("Bulk liking threads for pagination")
    random.seed(456)
    liked, skipped = 0, 0
    # Like every bulk thread with 2-4 random users
    for bi in range(len(BULK_THREAD_POOL)):
        idx = len(THREADS) + bi
        tid = thread_ids.get(idx)
        if not tid:
            continue
        author = _all_regular_users[bi % len(_all_regular_users)]
        likers = [u for u in _all_regular_users if u != author]
        random.shuffle(likers)
        for user in likers[:random.randint(2, 4)]:
            client = store.get(user)
            # Check if already liked
            status = client.get(f"/threads/{tid}/like/status")
            if status.status_code == 200 and status.json().get("liked"):
                skipped += 1
                continue
            resp = client.post(f"/threads/{tid}/like")
            if resp.status_code < 400:
                liked += 1
            time.sleep(0.05)
    print(f"  ✓ {liked} bulk likes added, {skipped} already liked")


def verify_data():
    step("Verifying seeded data")
    client = httpx.Client(base_url=API, timeout=30)

    # ── Thread pagination (page_size=20, expect 3+ pages) ────────────
    resp = client.get("/threads", params={"sort": "hot", "limit": 20})
    if _check(resp, "threads page 1"):
        body = resp.json()
        p1 = len(body.get("items", []))
        has_more = body.get("has_more", False)
        cursor = body.get("next_cursor")
        print(f"  ✓ Threads page 1: {p1} items, has_more={has_more}")
        # Fetch page 2
        if cursor:
            resp2 = client.get("/threads", params={"sort": "hot", "limit": 20, "cursor": cursor})
            if _check(resp2, "threads page 2"):
                b2 = resp2.json()
                p2 = len(b2.get("items", []))
                print(f"  ✓ Threads page 2: {p2} items, has_more={b2.get('has_more')}")
                # Fetch page 3
                if b2.get("next_cursor"):
                    resp3 = client.get("/threads", params={"sort": "hot", "limit": 20, "cursor": b2["next_cursor"]})
                    if _check(resp3, "threads page 3"):
                        p3 = len(resp3.json().get("items", []))
                        print(f"  ✓ Threads page 3: {p3} items")
                        print(f"  ✓ Thread pagination working: {p1}+{p2}+{p3} = {p1+p2+p3} total")

    # ── Comment pagination (thread 0 should have 55+ comments) ───────
    tid = thread_ids.get(0)
    if tid:
        resp = client.get(f"/threads/{tid}/comments", params={"sort": "new", "limit": 50})
        if _check(resp, "comments page 1"):
            body = resp.json()
            c1 = len(body.get("items", []))
            cursor = body.get("next_cursor")
            print(f"  ✓ Comments page 1 (thread 0): {c1} items, has_more={body.get('has_more')}")
            if cursor:
                resp2 = client.get(f"/threads/{tid}/comments", params={"sort": "new", "limit": 50, "cursor": cursor})
                if _check(resp2, "comments page 2"):
                    c2 = len(resp2.json().get("items", []))
                    print(f"  ✓ Comments page 2: {c2} items → comment pagination working")

    # ── Notification pagination (bob should have 30+ notifications) ──
    bob_client = store.get("bob")
    resp = bob_client.get("/notifications", params={"limit": 30})
    if _check(resp, "bob notifications page 1"):
        body = resp.json()
        n1 = len(body.get("items", []))
        has_more = body.get("has_more", False)
        print(f"  ✓ Bob notifications page 1: {n1} items, has_more={has_more}")
        if body.get("next_cursor"):
            resp2 = bob_client.get("/notifications", params={"limit": 30, "cursor": body["next_cursor"]})
            if _check(resp2, "bob notifications page 2"):
                n2 = len(resp2.json().get("items", []))
                print(f"  ✓ Bob notifications page 2: {n2} items → notification pagination working")

    # ── Unread count ──────────────────────────────────────────────────
    resp = bob_client.get("/notifications/unread-count")
    if _check(resp, "bob unread"):
        print(f"  ✓ Bob's unread notifications: {resp.json().get('count', 0)}")

    # ── Search ────────────────────────────────────────────────────────
    resp = client.get("/search/threads", params={"q": "Python"})
    if _check(resp, "search"):
        items = resp.json().get("items", [])
        print(f"  ✓ Search 'Python': {len(items)} results")

    # ── Dashboard (admin) ─────────────────────────────────────────────
    admin_client = store.get("admin")
    resp = admin_client.get("/dashboard/admin/stats")
    if _check(resp, "admin stats"):
        stats = resp.json()
        print(f"  ✓ Platform stats: {stats.get('total_users', '?')} users, "
              f"{stats.get('total_threads', '?')} threads, "
              f"{stats.get('total_comments', '?')} comments, "
              f"{stats.get('pending_reports', '?')} pending reports")

    client.close()


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  🌱 Real Time Discussion Forum — Seed Script")
    print(f"  Gateway: {GATEWAY}")
    print("=" * 60)

    try:
        login_admin()
        register_users()
        discover_existing_data()
        promote_moderator()
        update_profiles()
        create_threads()
        create_comments()
        like_threads()
        like_comments()
        edit_content()
        report_content()
        pin_threads()
        create_bulk_threads()
        create_bulk_comments()
        bulk_likes()
        verify_data()

        print("\n" + "=" * 60)
        print("  ✅ Seeding complete!")
        print("=" * 60)
        print("\n  Login credentials:")
        print("  ─────────────────────────────────────")
        print("  admin   / Admin@1234   (admin)")
        print("  alice   / Alice@1234   (moderator)")
        print("  bob     / Bob@12345    (member)")
        print("  carol   / Carol@1234   (member)")
        print("  dave    / Dave@1234    (member)")
        print("  eve     / Eve@12345    (member)")
        print()

    except httpx.ConnectError:
        print(f"\n  ✗ Could not connect to {GATEWAY}")
        print("    Make sure all services are running: docker compose up -d")
        sys.exit(1)
    finally:
        store.close_all()


if __name__ == "__main__":
    main()
