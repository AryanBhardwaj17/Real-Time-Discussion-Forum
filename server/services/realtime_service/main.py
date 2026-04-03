"""Realtime microservice — WebSocket connections with Redis Pub/Sub bridge.

This service has NO database. It:
1. Accepts WebSocket connections from clients (via the gateway)
2. Subscribes to Redis channels (thread:*, user:*, threads:*)
3. Forwards messages from Redis to connected WebSocket clients
"""

import asyncio
import json
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from shared.logging import setup_logging, get_logger
from shared.security import decode_access_token

from app.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════
# Connection Manager
# ═════════════════════════════════════════════════════════════════════

MAX_CONNECTIONS_PER_USER = 5
MAX_ANONYMOUS_CONNECTIONS = 100  # per-room cap for unauthenticated viewers
HEARTBEAT_INTERVAL = 30
MAX_WS_MESSAGE_SIZE = 65536  # 64 KB


class ConnectionManager:
    """Room-based WebSocket connection manager."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._user_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._ws_meta: dict[WebSocket, tuple[str, set[str]]] = {}

    async def connect(self, ws: WebSocket, user_id: str, room: str) -> bool:
        # Enforce per-user limit for authenticated users,
        # per-room anonymous cap for unauthenticated viewers
        if user_id == "anonymous":
            anon_count = sum(
                1 for w in self._rooms.get(room, set())
                if self._ws_meta.get(w, ("", set()))[0] == "anonymous"
            )
            if anon_count >= MAX_ANONYMOUS_CONNECTIONS:
                await ws.close(code=4009, reason="Too many anonymous connections")
                return False
        elif len(self._user_connections[user_id]) >= MAX_CONNECTIONS_PER_USER:
            await ws.close(code=4008, reason="Too many connections")
            return False

        await ws.accept()
        self._rooms[room].add(ws)
        self._user_connections[user_id].add(ws)

        if ws not in self._ws_meta:
            self._ws_meta[ws] = (user_id, set())
        self._ws_meta[ws][1].add(room)

        logger.info("ws_connected", user_id=user_id, room=room)
        return True

    def disconnect(self, ws: WebSocket) -> None:
        meta = self._ws_meta.pop(ws, None)
        if meta is None:
            return
        user_id, rooms = meta
        for room in rooms:
            self._rooms[room].discard(ws)
            if not self._rooms[room]:
                del self._rooms[room]
        self._user_connections[user_id].discard(ws)
        if not self._user_connections[user_id]:
            del self._user_connections[user_id]

    async def broadcast_to_room(self, room: str, data: dict) -> None:
        connections = list(self._rooms.get(room, set()))
        if not connections:
            return
        message = json.dumps(data)
        stale: list[WebSocket] = []
        for ws in connections:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
                else:
                    stale.append(ws)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)

    async def heartbeat(self, ws: WebSocket) -> None:
        try:
            while ws.client_state == WebSocketState.CONNECTED:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    @property
    def active_connections(self) -> int:
        return len(self._ws_meta)


manager = ConnectionManager()

# ═════════════════════════════════════════════════════════════════════
# Redis Pub/Sub Subscriber
# ═════════════════════════════════════════════════════════════════════

_redis_client: aioredis.Redis | None = None
_listener_task: asyncio.Task | None = None


async def _listen_loop() -> None:
    """Subscribe to Redis and forward messages to local WebSocket connections."""
    if _redis_client is None:
        logger.error("redis_not_initialized")
        return
    pubsub = _redis_client.pubsub()
    await pubsub.psubscribe("thread:*", "threads:*", "user:*")
    logger.info("redis_pubsub_subscribed")

    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                    await manager.broadcast_to_room(channel, data)
                except (json.JSONDecodeError, TypeError):
                    pass
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.punsubscribe()
        await pubsub.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _redis_client, _listener_task
    setup_logging(json_logs=not settings.DEBUG, log_level="DEBUG" if settings.DEBUG else "INFO", service_name="realtime")
    logger.info("realtime_service_startup")

    _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await _redis_client.ping()

    _listener_task = asyncio.create_task(_listen_loop())

    yield

    if _listener_task:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None

    logger.info("realtime_service_shutdown")


app = FastAPI(title="Realtime Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "realtime", "connections": str(manager.active_connections)}


# ═════════════════════════════════════════════════════════════════════
# WebSocket Endpoints
# ═════════════════════════════════════════════════════════════════════

def _authenticate_ws(token: str | None) -> str | None:
    """Validate JWT. Returns user_id or None."""
    if token is None:
        return None
    payload = decode_access_token(token, secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    if payload is None:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        uuid.UUID(sub)
    except ValueError:
        return None
    return sub


async def _wait_for_auth(ws: WebSocket, timeout: float = 5.0) -> str | None:
    """Wait for an auth message after WebSocket connect. Returns user_id or None."""
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=timeout)
        data = json.loads(raw)
        if data.get("type") == "auth" and "token" in data:
            return _authenticate_ws(data["token"])
    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
        pass
    return None


@app.websocket("/ws/threads/{thread_id}")
async def ws_thread(ws: WebSocket, thread_id: uuid.UUID) -> None:
    """WebSocket for live thread updates (new comments, likes).

    Auth protocol: connect → send {"type": "auth", "token": "..."} → join room.
    Anonymous viewing is allowed (skip auth message or send invalid token).
    """
    await ws.accept()

    # Wait for optional auth handshake
    user_id = await _wait_for_auth(ws) or "anonymous"
    room = f"thread:{thread_id}"

    # Enforce connection limits (anonymous per-room cap / per-user cap)
    if user_id == "anonymous":
        anon_count = sum(
            1 for w in manager._rooms.get(room, set())
            if manager._ws_meta.get(w, ("", set()))[0] == "anonymous"
        )
        if anon_count >= MAX_ANONYMOUS_CONNECTIONS:
            await ws.close(code=4009, reason="Too many anonymous connections")
            return
    elif len(manager._user_connections[user_id]) >= MAX_CONNECTIONS_PER_USER:
        await ws.close(code=4008, reason="Too many connections")
        return

    # Register in room
    manager._rooms[room].add(ws)
    manager._user_connections[user_id].add(ws)
    if ws not in manager._ws_meta:
        manager._ws_meta[ws] = (user_id, set())
    manager._ws_meta[ws][1].add(room)
    logger.info("ws_connected", user_id=user_id, room=room)

    heartbeat_task = asyncio.create_task(manager.heartbeat(ws))
    try:
        while True:
            data = await ws.receive_text()
            if len(data) > MAX_WS_MESSAGE_SIZE:
                await ws.close(code=1009, reason="Message too large")
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_thread_error", thread_id=str(thread_id))
    finally:
        heartbeat_task.cancel()
        manager.disconnect(ws)


@app.websocket("/ws/feed")
async def ws_feed(ws: WebSocket) -> None:
    """WebSocket for live homepage feed updates (new threads, edits, deletes, pin/lock).

    Auth is optional — anonymous viewers can watch the feed.
    """
    await ws.accept()

    user_id = await _wait_for_auth(ws) or "anonymous"
    room = "threads:feed"

    if user_id == "anonymous":
        anon_count = sum(
            1 for w in manager._rooms.get(room, set())
            if manager._ws_meta.get(w, ("", set()))[0] == "anonymous"
        )
        if anon_count >= MAX_ANONYMOUS_CONNECTIONS:
            await ws.close(code=4009, reason="Too many anonymous connections")
            return
    elif len(manager._user_connections[user_id]) >= MAX_CONNECTIONS_PER_USER:
        await ws.close(code=4008, reason="Too many connections")
        return

    manager._rooms[room].add(ws)
    manager._user_connections[user_id].add(ws)
    if ws not in manager._ws_meta:
        manager._ws_meta[ws] = (user_id, set())
    manager._ws_meta[ws][1].add(room)
    logger.info("ws_connected", user_id=user_id, room=room)

    heartbeat_task = asyncio.create_task(manager.heartbeat(ws))
    try:
        while True:
            data = await ws.receive_text()
            if len(data) > MAX_WS_MESSAGE_SIZE:
                await ws.close(code=1009, reason="Message too large")
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_feed_error")
    finally:
        heartbeat_task.cancel()
        manager.disconnect(ws)


@app.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket) -> None:
    """WebSocket for personal notifications. Requires authentication.

    Auth protocol: connect → send {"type": "auth", "token": "..."} → join room.
    """
    await ws.accept()

    user_id = await _wait_for_auth(ws)
    if user_id is None:
        await ws.close(code=4001, reason="Authentication required")
        return

    room = f"user:{user_id}"

    manager._rooms[room].add(ws)
    manager._user_connections[user_id].add(ws)
    if ws not in manager._ws_meta:
        manager._ws_meta[ws] = (user_id, set())
    manager._ws_meta[ws][1].add(room)
    logger.info("ws_connected", user_id=user_id, room=room)

    heartbeat_task = asyncio.create_task(manager.heartbeat(ws))
    try:
        while True:
            data = await ws.receive_text()
            if len(data) > MAX_WS_MESSAGE_SIZE:
                await ws.close(code=1009, reason="Message too large")
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_notifications_error", user_id=user_id)
    finally:
        heartbeat_task.cancel()
        manager.disconnect(ws)
