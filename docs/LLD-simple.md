# Low-Level Design (Simple) — Real-Time Discussion Forum

> A plain-text, diagram-free companion to the [detailed LLD](./LLD.md).  
> Designed for quick skimming — every section uses standard markdown tables.

---

## 1. Database Schema

Each service owns a separate PostgreSQL instance. No cross-service DB queries.

### 1.1 Auth DB

**users**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| email | VARCHAR(320) | UNIQUE, NOT NULL |
| username | VARCHAR(50) | UNIQUE, NOT NULL |
| password_hash | VARCHAR | bcrypt, NOT NULL |
| name | VARCHAR | nullable |
| avatar_url | VARCHAR | nullable |
| bio | TEXT | nullable |
| role | VARCHAR(20) | FK → roles.code, default `member` |
| is_active | BOOLEAN | default true |
| deactivated_by_admin | BOOLEAN | default false |
| created_at | TIMESTAMPTZ | server default |
| updated_at | TIMESTAMPTZ | auto-update |

**refresh_tokens**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| user_id | UUID | FK → users.id |
| token_hash | VARCHAR | UNIQUE (SHA-256 of raw token) |
| expires_at | TIMESTAMPTZ | 7-day TTL |
| is_revoked | BOOLEAN | default false |
| replaced_by | UUID | FK → refresh_tokens.id (rotation chain) |
| created_at | TIMESTAMPTZ | server default |

**roles** — Lookup table: `admin`, `moderator`, `member`.

### 1.2 Content DB

**threads**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| title | VARCHAR(300) | NOT NULL, bleach-sanitized |
| description | TEXT | NOT NULL, bleach-sanitized |
| author_id | UUID | NOT NULL (opaque FK to Auth) |
| author_username | VARCHAR(50) | denormalized at write time |
| author_role | VARCHAR(20) | denormalized at write time |
| like_count | INTEGER | denormalized counter, default 0 |
| comment_count | INTEGER | denormalized counter, default 0 |
| hot_score | FLOAT | pre-computed: log₁₀(max(likes,1)) + timestamp/45000 |
| pinned_at | TIMESTAMPTZ | nullable — `is_pinned = pinned_at IS NOT NULL` |
| locked_at | TIMESTAMPTZ | nullable — `is_locked = locked_at IS NOT NULL` |
| locked_by | UUID | nullable |
| is_deleted | BOOLEAN | soft delete, default false |
| author_is_active | BOOLEAN | default true (toggled on user deactivation) |
| edited_at | TIMESTAMPTZ | nullable — `is_edited = edited_at IS NOT NULL` |
| created_at | TIMESTAMPTZ | server default |
| updated_at | TIMESTAMPTZ | auto-update |

**comments**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| content | TEXT | NOT NULL, bleach-sanitized |
| thread_id | UUID | FK → threads.id |
| author_id | UUID | NOT NULL |
| author_username | VARCHAR(50) | denormalized |
| author_role | VARCHAR(20) | denormalized |
| parent_id | UUID | FK → comments.id (self-ref, NULL = top-level) |
| depth | INTEGER | 0 = top-level |
| like_count | INTEGER | default 0 |
| reply_count | INTEGER | default 0 |
| is_deleted | BOOLEAN | soft delete |
| author_is_active | BOOLEAN | default true |
| edited_at | TIMESTAMPTZ | nullable |
| created_at | TIMESTAMPTZ | server default |
| updated_at | TIMESTAMPTZ | auto-update |

**thread_likes** / **comment_likes**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| user_id | UUID | NOT NULL |
| thread_id / comment_id | UUID | FK |
| created_at | TIMESTAMPTZ | server default |

Unique constraint: `(user_id, thread_id)` / `(user_id, comment_id)` — one like per user.

**reports**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| reporter_id | UUID | NOT NULL |
| target_type | VARCHAR | `thread` or `comment` |
| target_id | UUID | NOT NULL |
| reason | VARCHAR | FK → report_reasons.code |
| description | TEXT | nullable |
| status | VARCHAR | FK → report_statuses.code, default `pending` |
| reviewed_by | UUID | nullable |
| reviewed_at | TIMESTAMPTZ | nullable |
| created_at | TIMESTAMPTZ | server default |

**tags** — `id` (serial PK), `name` (UNIQUE), `usage_count`.  
**thread_tags** — junction table: `(thread_id, tag_id)` composite PK.  
**report_reasons** / **report_statuses** — lookup tables.

### 1.3 Notification DB

**notifications**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| user_id | UUID | recipient |
| type | VARCHAR | FK → notification_types.code |
| reference_type | VARCHAR | `thread` or `comment` |
| reference_id | UUID | NOT NULL |
| actor_id | UUID | who triggered it |
| thread_id | UUID | nullable, for click-to-navigate |
| content | TEXT | notification text |
| is_read | BOOLEAN | default false |
| created_at | TIMESTAMPTZ | server default |

Idempotency: `UNIQUE(user_id, actor_id, type, reference_id)` prevents duplicate notifications.

**notification_types** — lookup table: `reply`, `mention`, `like`.

### 1.4 Dashboard DB

**audit_logs**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID (v7) | PK |
| actor_id | UUID | nullable |
| action | VARCHAR(50) | e.g. `role_changed`, `user_deactivated` |
| target_type | VARCHAR(20) | e.g. `user`, `thread` |
| target_id | UUID | NOT NULL |
| details | JSONB | nullable, extra context |
| created_at | TIMESTAMPTZ | append-only |

### 1.5 Key Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| users | email, username (UNIQUE) | Fast login lookup |
| threads | hot_score (WHERE NOT deleted) | "Hot" sort — partial B-tree |
| threads | created_at (WHERE NOT deleted) | "New" sort — partial B-tree |
| comments | (thread_id, created_at) WHERE NOT deleted | Comment listing |
| thread_likes | (user_id, thread_id) UNIQUE | One like per user |
| comment_likes | (user_id, comment_id) UNIQUE | One like per user |
| notifications | (user_id, is_read, created_at) | Unread listing |
| refresh_tokens | token_hash UNIQUE | Token lookup |

---

## 2. Key Flows (Step-by-Step)

### 2.1 User Registration

1. Client sends `POST /auth/register {email, username, password}` to Gateway.
2. Gateway forwards to Auth service (rate limit: 10/min).
3. Auth validates input (Pydantic), checks for duplicate email/username.
4. Password hashed with bcrypt, user row inserted.
5. Returns `201 {id, email, username, role: "member"}`.

### 2.2 Login

1. Client sends `POST /auth/login {login, password}`.
2. Auth looks up user by email or username, verifies bcrypt hash.
3. If user was self-deactivated, auto-reactivates. If admin-deactivated, rejects.
4. Generates JWT access token (30 min) + opaque refresh token (7 days).
5. Refresh token SHA-256 hashed and stored in DB.
6. Gateway intercepts the response, extracts tokens, sets HttpOnly + SameSite=lax cookies, returns JSON body without raw tokens.

### 2.3 Refresh Token Rotation

1. Client sends `POST /auth/refresh` (refresh_token comes from cookie).
2. Auth hashes the token, looks up in DB.
3. **If already revoked** → theft detected → revoke ALL user tokens (family revocation) → return 401.
4. **If valid** → revoke old token → create new access + refresh pair → link old→new via `replaced_by` → return new pair.

### 2.4 Create Thread

1. Client sends `POST /threads/ {title, description, tags}` with JWT cookie.
2. Gateway validates JWT, injects `X-User-ID`, `X-User-Role`, `X-User-Username` headers.
3. Content service sanitizes inputs with `bleach.clean()` (strips all HTML).
4. Computes `hot_score = log₁₀(max(likes,1)) + created_at.timestamp() / 45000`.
5. Inserts thread + tag relationships in DB.
6. Publishes `threads:feed` event via Redis Pub/Sub (→ WebSocket broadcast).
7. Queues Meilisearch indexing via Redis Stream.
8. Returns `201 ThreadRead`.

### 2.5 Post Comment with @Mention

1. Client sends `POST /threads/{id}/comments/ {content: "Hey @alice!"}`.
2. Content service verifies thread exists and is not locked.
3. If reply: validates parent exists, belongs to same thread.
4. Sanitizes content, inserts comment, increments `thread.comment_count`.
5. Publishes `thread:{id}` event via Redis Pub/Sub.
6. Regex-extracts @mentions from content.
7. Resolves usernames → user IDs via Auth internal API (`POST /internal/users/lookup-usernames` with `X-Internal-Secret`, protected by circuit breaker).
8. Pushes REPLY notification (for thread author) + MENTION notifications (for each @mentioned user) to `stream:notifications`.
9. Notification service consumer reads stream, inserts notification rows, publishes `user:{id}` via Redis Pub/Sub.
10. Realtime service forwards to WebSocket clients.

### 2.6 Like Toggle

1. Client sends `POST /threads/{id}/like`.
2. Content service checks if `thread_likes` row exists for this user + thread.
3. **Not liked** → INSERT like, increment `like_count`, recalculate `hot_score`, update Meilisearch.
4. **Already liked** → DELETE like, decrement `like_count`, recalculate `hot_score`.
5. Publishes like event via Redis Pub/Sub → real-time broadcast to all clients viewing the thread.

### 2.7 Full-Text Search

1. Client sends `GET /search/threads?q=kuberntes` (note: typo).
2. Search service sends query to Meilisearch (typo tolerance corrects to "kubernetes").
3. Meilisearch returns full thread documents — no database query needed.
4. Returns `CursorPage<ThreadSearchResult>`.

### 2.8 Account Deactivation

1. Admin sends `POST /admin/users/{id}/deactivate`.
2. Auth sets `is_active=false`, `deactivated_by_admin=true`, revokes all refresh tokens.
3. Publishes `stream:user_updates {type: user_status_changed, is_active: false}`.
4. Content service consumer updates all threads/comments by that author: `author_is_active=false`.
5. Threads hidden from listings. Comments show `[account deactivated]`.
6. On reactivation: reverse the above — all content restored.

---

## 3. API Contracts

### Auth Service

| Method | Endpoint | Auth | Response |
|--------|----------|------|----------|
| POST | `/auth/register` | No | 201 User |
| POST | `/auth/login` | No | 200 Tokens |
| POST | `/auth/refresh` | No | 200 Tokens |
| POST | `/auth/logout` | Yes | 200 |
| GET | `/users/me` | Yes | 200 User |
| PATCH | `/users/me` | Yes | 200 User |
| POST | `/auth/change-password` | Yes | 200 |
| PATCH | `/users/me/deactivate` | Yes | 200 |
| DELETE | `/users/me` | Yes | 200 |
| GET | `/admin/users` | Admin | 200 CursorPage\<User\> |
| GET | `/admin/users/{id}` | Admin | 200 User |
| PATCH | `/admin/users/{id}/role` | Admin | 200 User |
| POST | `/admin/users/{id}/deactivate` | Admin | 200 |
| POST | `/admin/users/{id}/reactivate` | Admin | 200 |

### Content Service

| Method | Endpoint | Auth | Response |
|--------|----------|------|----------|
| GET | `/threads/` | No | 200 CursorPage\<Thread\> |
| POST | `/threads/` | Yes | 201 Thread |
| GET | `/threads/{id}` | No | 200 Thread |
| PATCH | `/threads/{id}` | Author | 200 Thread |
| DELETE | `/threads/{id}` | Author/Mod+ | 200 |
| POST | `/threads/{id}/like` | Yes | 200 {liked, like_count} |
| POST | `/threads/{id}/pin` | Mod+ | 200 Thread |
| POST | `/threads/{id}/lock` | Mod+ | 200 Thread |
| GET | `/threads/{id}/likers` | No | 200 CursorPage\<Liker\> |
| POST | `/threads/{id}/comments/` | Yes | 201 Comment |
| GET | `/threads/{id}/comments/` | No | 200 CursorPage\<Comment\> |
| GET | `/comments/{id}/replies` | No | 200 CursorPage\<Comment\> |
| PATCH | `/comments/{id}` | Author | 200 Comment |
| DELETE | `/comments/{id}` | Author/Mod+ | 200 |
| POST | `/comments/{id}/like` | Yes | 200 {liked, like_count} |
| POST | `/threads/{id}/report` | Yes | 201 Report |
| GET | `/reports` | Mod+ | 200 CursorPage\<Report\> |
| POST | `/reports/{id}/resolve` | Mod+ | 200 Report |

### Search, Notification, Dashboard

| Method | Endpoint | Auth | Response |
|--------|----------|------|----------|
| GET | `/search/threads` | No | 200 CursorPage\<Thread\> |
| GET | `/notifications/` | Yes | 200 CursorPage\<Notification\> |
| GET | `/notifications/unread-count` | Yes | 200 {count} |
| POST | `/notifications/{id}/read` | Yes | 200 |
| POST | `/notifications/read-all` | Yes | 200 {marked} |
| GET | `/dashboard/me/threads` | Yes | 200 CursorPage\<Thread\> |
| GET | `/dashboard/me/stats` | Yes | 200 Stats |
| GET | `/dashboard/mod/activity` | Mod+ | 200 Activity |
| GET | `/dashboard/admin/stats` | Admin | 200 Stats |
| GET | `/dashboard/admin/audit-log` | Admin | 200 CursorPage\<AuditLog\> |

### Internal APIs (inter-service, `X-Internal-Secret` required)

| From → To | Endpoint | Purpose |
|-----------|----------|---------|
| Content → Auth | `POST /internal/users/lookup-usernames` | Resolve @mentions to UUIDs |
| Dashboard → Auth | `GET /internal/stats` | User aggregate stats |
| Dashboard → Content | `GET /internal/stats` | Content aggregate stats |
| Dashboard → Content | `GET /internal/activity` | Recent activity feed |

### Pagination Contract

All paginated endpoints return:

```
{ "items": [...], "next_cursor": "opaque-string" | null, "has_more": true | false }
```

---

## 4. Event Contracts

### Redis Pub/Sub (Ephemeral — real-time broadcast)

| Channel Pattern | Events | Publisher |
|----------------|--------|----------|
| `threads:feed` | new/updated/deleted threads, pin/lock toggles, like counts, new comments | Content |
| `thread:<id>` | new/edited/deleted comments, like toggles, pin/lock changes | Content |
| `user:<id>` | new notification, force logout, role changed | Notification / Auth |

### Redis Streams (Durable — at-least-once delivery)

| Stream | Publisher → Consumer | Purpose |
|--------|---------------------|---------|
| `stream:notifications` | Content → Notification | Create notification rows |
| `stream:audit` | Content/Auth → Dashboard | Insert audit log entries |
| `stream:user_updates` | Auth → Content | Username changes, account status changes |
| `stream:meili_indexing` | Content → Content | Index/update/delete threads in Meilisearch |

Each stream has a dead-letter queue (`stream:<name>:dead`) with a 3-retry policy.

### WebSocket Endpoints

| Path | Room | Auth | Purpose |
|------|------|------|---------|
| `/ws/threads/{id}` | `thread:<id>` | Optional | Live comments, likes, edits, pin/lock |
| `/ws/feed` | `threads:feed` | Optional | Homepage feed updates |
| `/ws/notifications` | `user:<id>` | Required | Personal notifications, force logout |

---

## 5. Role-Based Access Control

Three roles: **Admin > Moderator > Member**.

| Action | Member | Moderator | Admin |
|--------|--------|-----------|-------|
| Create thread/comment | Own | Own | Own |
| Edit thread/comment | Own only | Own only | Own only |
| Delete thread/comment | Own only | Own + any below their role | Own + any below their role |
| Pin/Lock thread | No | Yes (except admin-authored) | Yes (except admin-authored) |
| Resolve reports | No | Yes | Yes |
| Manage users/roles | No | No | Yes |
| View admin dashboard | No | No | Yes |
| View mod activity feed | No | Yes | Yes |

**Hierarchy enforcement**: `_can_moderate(actor_role, author_role)` returns `True` only if actor is strictly above author. Moderators cannot moderate other moderator or admin content. Owner bypass: users can always pin/lock/delete their own content.

---

## 6. State Machines

### Thread Lifecycle

- **Active** → Mod pins → **Pinned** → Mod unpins → **Active**
- **Active** → Mod locks → **Locked** (no new comments) → Mod unlocks → **Active**
- **Active / Pinned / Locked** → Author/Mod deletes → **Soft-Deleted** (hidden from listings)

### Comment Lifecycle

- **Active** → Author edits → **Edited** (edited_at set, `is_edited` flag)
- **Active / Edited** → Author/Mod deletes → **Soft-Deleted** (content replaced with `[deleted]`, replies preserved)

### Refresh Token Lifecycle

- **Active** → used in `/refresh` → **Rotated** (new token linked via `replaced_by`)
- **Active** → 7 days pass → **Expired**
- **Active** → logout / password change → **Revoked**
- **Rotated** → old token reused → **Family Revoked** (ALL user tokens revoked — theft detection)

---

## 7. Error Handling

All services return errors in a consistent format: `{"detail": "error message"}`.

| Scenario | HTTP Status | Example Detail |
|----------|-------------|----------------|
| Resource not found | 404 | "Thread not found" |
| Duplicate email/username | 409 | "Email already registered" |
| Invalid/expired JWT | 401 | "Invalid or expired token" |
| Wrong password | 401 | "Invalid credentials" |
| Insufficient role | 403 | "Insufficient permissions" |
| Thread is locked | 403 | "Thread is locked" |
| Edit someone else's content | 403 | "You can only edit your own" |
| Mod acting on admin content | 403 | "Moderators cannot delete/pin/lock admin content" |
| Validation error | 422 | Field-level Pydantic errors |
| Rate limit exceeded | 429 | "Rate limit exceeded" |

---

> **For the full version with Mermaid diagrams, ER diagrams, sequence diagrams, and class structure charts, see [LLD.md](./LLD.md).**
