# Real-Time Discussion Forum

A production-grade Reddit / Discord-style discussion forum built as a **microservice architecture** using **FastAPI**, **PostgreSQL**, **Redis**, **Meilisearch**, and **React**.

Fully containerized — a single `docker compose up` starts all **14 containers** (frontend + 7 backend services + 4 PostgreSQL databases + Redis + Meilisearch).

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Environment Variables](#environment-variables)
- [Architecture Decisions](#architecture-decisions)
- [Documentation](#documentation)

---

## Features

- **Authentication & Authorization** — JWT access/refresh tokens with rotation & theft detection, password change, role-based access control (Member → Moderator → Admin)
- **Threads & Comments** — Full CRUD with nested replies (depth tracking), soft deletes with `[deleted]` masking, cursor-based pagination, hot/new/top sorting (Reddit-style hot score)
- **Likes** — Toggle-based liking on threads and comments with atomic counter updates
- **Real-Time** — WebSocket connections with Redis Pub/Sub for live broadcast of new threads, comments, likes, and notifications
- **Full-Text Search** — Meilisearch-powered typo-tolerant search across threads (title, description, tags, author)
- **Notifications** — Reply, mention (@username), and like notifications with unread counts, delivered in real-time via WebSocket
- **Reports & Moderation** — Content reporting system with mod/admin review workflow; thread pinning and locking with role hierarchy enforcement
- **Dashboards** — Personal stats (member), recent activity (moderator), platform-wide analytics (admin)
- **Audit Logging** — All privileged actions recorded via event-driven audit trail
- **Rate Limiting** — Centralized rate limiting at the API Gateway via SlowAPI
- **Content Sanitization** — HTML/XSS sanitization via bleach on all user input

---

## Architecture

```
┌─────────────────┐
│  React SPA      │
│    (:3000)      │
└────────┬────────┘
         │ /api, /ws reverse proxy
┌────────▼───────────────────────────────────────────────┐
│             API Gateway (:8000)                         │
│   JWT Validation · Rate Limiting · CORS · Routing       │
└──┬───────┬────────┬────────┬───────┬───────┬───────────┘
   │       │        │        │       │       │
┌──▼──┐ ┌──▼───┐ ┌──▼───┐ ┌──▼──┐ ┌──▼───┐ ┌▼────────┐
│Auth │ │Content│ │Notif │ │Search│ │Dash  │ │Realtime │
└──┬──┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └────┬────┘
   │       │        │        │        │           │
┌──▼──┐ ┌──▼───┐ ┌──▼───┐ ┌──▼────┐  │     ┌─────▼────┐
│Auth │ │Content│ │Notif │ │Meili- │  │     │  Redis   │
│ DB  │ │  DB   │ │  DB  │ │search │  │     │ Pub/Sub  │
└─────┘ └──────┘ └──────┘ └───────┘  │     │+ Streams │
                                ┌─────▼────┐└──────────┘
                                │Dashboard │
                                │    DB    │
                                └──────────┘
```

| Service | Owns | Responsibilities |
|---------|------|-----------------|
| **API Gateway** | — | Stateless JWT validation, header injection, reverse proxy, rate limiting, CORS |
| **Auth** | Users, Tokens | Register, login, JWT + refresh token rotation with theft detection, password change, role management |
| **Content** | Threads, Comments, Likes, Reports | CRUD, moderation (pin/lock/delete), Meilisearch indexing, @mention resolution, like toggle |
| **Notification** | Notifications | Event-driven notification creation, listing, mark-read |
| **Search** | — | Typo-tolerant full-text search (reads Meilisearch directly, no DB) |
| **Dashboard** | Audit Logs | Admin stats, audit trail, moderator activity feed, personal user stats |
| **Realtime** | — | WebSocket rooms, Redis Pub/Sub → WebSocket bridge, heartbeat |

### Inter-Service Communication

- **Synchronous**: Client → Gateway → services via HTTP proxy; Dashboard → Auth/Content via internal HTTP APIs; Content → Auth for @mention resolution (with circuit breaker)
- **Asynchronous**: Redis Pub/Sub (ephemeral real-time broadcasts) + Redis Streams (durable event delivery with DLQ + 3-retry policy)
- **Cross-service data**: Author usernames/roles denormalized at write time — no cross-service DB queries

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI 0.115, Uvicorn |
| Databases | PostgreSQL 16 (4 separate instances — one per service) |
| Cache / Events | Redis 7 (Pub/Sub + Streams) |
| Search | Meilisearch 1.12 |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Migrations | Alembic (auto-runs on startup) |
| Auth | PyJWT (HS256) + bcrypt |
| Real-Time | WebSockets + Redis Pub/Sub bridge |
| Frontend | React 19, Vite 8, Tailwind CSS 4.2, Axios |
| Logging | structlog (JSON in production, console in dev) |
| Containers | Docker + Docker Compose (14 containers) |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd "Real Time Discussion Forum"
```

Create a `.env` file (or copy from `.env.example`) and set a strong `SECRET_KEY`:

```
SECRET_KEY=your-random-64-char-hex-string
```

### 2. Start everything

```bash
docker compose up --build -d
```

This starts **14 containers**:

| Container | Role | Port |
|-----------|------|------|
| **forum_frontend** | React SPA | `3000` |
| **forum_gateway** | API Gateway (single entry point) | `8000` |
| **forum_auth** | Auth Service | — |
| **forum_content** | Content Service | — |
| **forum_notification** | Notification Service | — |
| **forum_search** | Search Service | — |
| **forum_dashboard** | Dashboard Service | — |
| **forum_realtime** | Realtime Service | — |
| **forum_postgres_auth** | PostgreSQL — auth_db | — |
| **forum_postgres_content** | PostgreSQL — content_db | — |
| **forum_postgres_notification** | PostgreSQL — notification_db | — |
| **forum_postgres_dashboard** | PostgreSQL — dashboard_db | — |
| **forum_redis** | Redis 7 | — |
| **forum_meilisearch** | Meilisearch 1.12 | — |

Only the **frontend (port 3000)** and **gateway (port 8000)** are exposed to the host.  
Database migrations run automatically on startup via **Alembic**.

### 3. Access the application

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Gateway health check**: `curl http://localhost:8000/health`

### 4. Seed test data (optional)

```bash
pip install httpx
python scripts/seed.py
```

This creates 6 users, 10 threads, 42 comments, likes, reports, and pins — enough to test every feature.

| User | Password | Role |
|------|----------|------|
| `admin` | `Admin@1234` | Admin |
| `alice` | `Alice@1234` | Moderator |
| `bob` | `Bob@12345` | Member |
| `carol` | `Carol@1234` | Member |
| `dave` | `Dave@1234` | Member |
| `eve` | `Eve@12345` | Member |

### 5. Frontend development mode (optional)

For hot-reload during frontend development:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` → `http://localhost:8000` and `/ws` → `ws://localhost:8000`.

---

## Project Structure

```
├── services/
│   ├── shared/              # Shared library (base models, security, exceptions, logging)
│   ├── gateway/             # API Gateway (JWT validation, routing, rate limiting)
│   ├── auth/                # Auth Service (users, tokens, password flows)
│   ├── content/             # Content Service (threads, comments, likes, reports)
│   ├── notification/        # Notification Service (event-driven notifications)
│   ├── search/              # Search Service (Meilisearch queries, no DB)
│   ├── dashboard/           # Dashboard Service (stats aggregation, audit log)
│   └── realtime/            # Realtime Service (WebSocket rooms, Redis bridge)
├── frontend/                # React SPA (Vite + Tailwind, served via nginx in production)
├── tests/                   # Integration & smoke tests
├── scripts/
│   └── seed.py              # Database seed script
├── docs/
│   ├── HLD.md               # High-Level Design
│   ├── LLD.md               # Low-Level Design (with diagrams)
│   ├── LLD-simple.md        # Low-Level Design (plain text, reviewer-friendly)
│   ├── technical-highlights.md  # Technical assessment & USPs
│   └── deep-dive/           # 13-part deep-dive walkthrough
├── docker-compose.yml       # Full 14-container orchestration
├── Makefile                 # Common dev commands (make help)
└── .env                     # Environment variables (not committed)
```

Each backend service follows a consistent layout:

```
services/<name>/
├── main.py                  # FastAPI app, lifespan, health endpoint
├── pyproject.toml           # Dependencies
├── Dockerfile               # Multi-stage build with shared library
├── app/
│   ├── config.py            # Pydantic settings
│   ├── db.py                # Database engine & async session
│   ├── models.py            # SQLAlchemy models (or models/ sub-package)
│   ├── schemas.py           # Pydantic schemas (or schemas/ sub-package)
│   ├── routes.py            # API route handlers (or routes/ sub-package)
│   ├── services.py          # Business logic (or services/ sub-package)
│   └── repositories/        # Data access layer (Auth & Content)
└── tests/
    ├── conftest.py           # Shared fixtures
    └── test_<domain>.py      # Domain-specific test modules
```

> Auth and Content services use **sub-packages** (`models/`, `schemas/`, `routes/`, `services/`) with `__init__.py` re-exports. Smaller services keep flat files.

---

## API Endpoints

All endpoints are accessed through the **API Gateway** at `http://localhost:8000/api/v1`.

### Auth (`/auth`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/register` | Create account | — |
| POST | `/login` | Get access + refresh tokens | — |
| POST | `/refresh` | Rotate refresh token | — |
| POST | `/logout` | Revoke refresh token | ✓ |
| POST | `/change-password` | Change current password | ✓ |

### Users (`/users`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/me` | Get current user profile | ✓ |
| PATCH | `/me` | Update profile (name, bio, avatar) | ✓ |
| PATCH | `/me/deactivate` | Deactivate own account | ✓ |
| DELETE | `/me` | Permanently delete account | ✓ |

### Threads (`/threads`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/` | List threads (sort: hot/new/top, cursor pagination) | — |
| POST | `/` | Create thread | ✓ |
| GET | `/{id}` | Get thread by ID | — |
| PATCH | `/{id}` | Update thread (author only) | ✓ |
| DELETE | `/{id}` | Soft delete thread (author/mod/admin) | ✓ |
| POST | `/{id}/like` | Toggle like | ✓ |
| GET | `/{id}/likers` | List users who liked | — |
| POST | `/{id}/report` | Report thread | ✓ |
| POST | `/{id}/pin` | Pin/unpin (mod/admin) | ✓ |
| POST | `/{id}/lock` | Lock/unlock (mod/admin) | ✓ |

### Comments

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/threads/{id}/comments` | List comments (cursor pagination) | — |
| POST | `/threads/{id}/comments` | Create comment (with optional `parent_id` for nesting) | ✓ |
| GET | `/comments/{id}/replies` | List replies to a comment | — |
| PATCH | `/comments/{id}` | Update comment (author only) | ✓ |
| DELETE | `/comments/{id}` | Soft delete comment | ✓ |
| POST | `/comments/{id}/like` | Toggle like | ✓ |
| GET | `/comments/{id}/likers` | List users who liked | — |
| POST | `/comments/{id}/report` | Report comment | ✓ |

### Search (`/search`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/threads?q=query` | Typo-tolerant full-text search | — |

### Notifications (`/notifications`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/` | List notifications (cursor pagination, `unread_only` filter) | ✓ |
| GET | `/unread-count` | Get unread count | ✓ |
| POST | `/{id}/read` | Mark one as read | ✓ |
| POST | `/read-all` | Mark all as read | ✓ |

### Dashboard (`/dashboard`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/me/threads` | My threads | ✓ |
| GET | `/me/comments` | My comments | ✓ |
| GET | `/me/stats` | My stats | ✓ |
| GET | `/mod/activity` | Recent activity feed | Mod+ |
| GET | `/admin/stats` | Platform-wide statistics | Admin |
| GET | `/admin/audit-log` | Audit log | Admin |

### Admin (`/admin`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/users` | List all users | Admin |
| GET | `/users/{id}` | Get user details | Admin |
| PATCH | `/users/{id}/role` | Change user role | Admin |
| POST | `/users/{id}/deactivate` | Ban user | Admin |
| POST | `/users/{id}/reactivate` | Unban user | Admin |

### WebSocket

| Path | Description |
|------|-------------|
| `/ws/threads/{id}` | Live thread updates (comments, likes, pin/lock) |
| `/ws/feed` | Homepage feed updates (new threads, counts) |
| `/ws/notifications` | Personal notification stream (requires auth) |

---

## Database Schema

Each service owns a separate PostgreSQL **instance** — true infrastructure-level isolation:

| Database | Tables |
|----------|--------|
| **auth_db** | `users`, `refresh_tokens`, `roles` |
| **content_db** | `threads`, `comments`, `thread_likes`, `comment_likes`, `reports`, `tags`, `thread_tags`, `report_reasons`, `report_statuses` |
| **notification_db** | `notifications`, `notification_types` |
| **dashboard_db** | `audit_logs` |

See [LLD-simple.md](docs/LLD-simple.md) for column-level schema details.

---

## Testing

Each service has its own test suite under `services/<name>/tests/`.

```bash
# Run tests for a specific service (inside Docker)
docker compose exec content python -m pytest tests/ -v
docker compose exec auth python -m pytest tests/ -v

# Run smoke tests (all services health check)
python tests/smoke_microservices.py
```

| Service | Test Modules | Coverage |
|---------|-------------|----------|
| Auth | register, login, profile, health | 22 tests |
| Content | threads, comments, likes, reports, moderation, health | 62 tests |
| Notification | list, mark_read, health | Per-module |
| Search | search, health | Per-module |
| Dashboard | admin, moderator, member, health | Per-module |
| Gateway | health, jwt, routing | Per-module |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — (required) | JWT signing key (shared by Gateway, Auth, Realtime) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token TTL |
| `DEBUG` | `true` | Enable debug logging |
| `MEILI_MASTER_KEY` | `forum_meili_master_key` | Meilisearch master key |
| `POSTGRES_PASSWORD` | `forum_pass` | PostgreSQL password (all 4 instances) |
| `REDIS_PASSWORD` | `forum_redis_pass` | Redis password |

Database URLs, Redis URLs, and inter-service URLs are configured in `docker-compose.yml`.

---

## Makefile

Common commands via `make`:

```bash
make build      # Build and start all 14 containers
make logs       # Tail all logs
make logs-auth  # Tail logs for a specific service
make rebuild-content  # Rebuild a single service
make seed       # Seed the database with test data
make frontend   # Start frontend dev server (hot-reload)
make smoke      # Run smoke tests
make help       # Show all available commands
```

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **7 microservices** | Clear data ownership boundaries; independent scaling and deployment; failure isolation |
| **API Gateway pattern** | Single entry point; centralized JWT validation, header injection (`X-User-ID`, `X-User-Role`, `X-User-Username`), rate limiting, CORS |
| **Database per service** | 4 separate PostgreSQL instances — true infrastructure isolation, independent backups/upgrades |
| **Redis Pub/Sub + Streams** | Pub/Sub for ephemeral real-time broadcasts; Streams for durable event delivery with consumer groups and DLQ |
| **Cursor-based pagination** | No offset drift; stable traversal under concurrent inserts/deletes |
| **Denormalized usernames** | Avoids cross-service DB queries; accepted trade-off of eventual consistency |
| **Soft deletes** | Comments with replies show `[deleted]` instead of being removed — preserves thread structure |
| **Shared library** | Common code (base models, security, exceptions, logging, middleware) as an installable Python package |
| **Circuit breaker** | Protects inter-service HTTP calls (Content → Auth for @mentions) from cascading failures |

---
