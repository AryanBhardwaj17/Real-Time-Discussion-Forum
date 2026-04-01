"""Redis client for the Content service — Streams + Pub/Sub.

Uses Redis Streams (XADD) for durable event delivery to consumers
(notifications, audit logs) and Pub/Sub for ephemeral real-time
broadcasts (WebSocket updates via the Realtime service).
"""

import json

import redis.asyncio as aioredis

from shared.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

_redis: aioredis.Redis | None = None


async def connect_redis() -> aioredis.Redis:
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True, max_connections=20)
    await _redis.ping()
    logger.info("redis_connected")
    return _redis


async def disconnect_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not connected")
    return _redis


async def publish(channel: str, data: dict) -> None:
    """Publish a message via Pub/Sub for ephemeral real-time broadcasts."""
    r = get_redis()
    await r.publish(channel, json.dumps(data))


async def stream_add(stream: str, data: dict, maxlen: int = 10000) -> str:
    """Append a message to a Redis Stream for durable delivery.

    Returns the message ID assigned by Redis.
    Uses approximate trimming (~maxlen) to cap memory usage.
    """
    r = get_redis()
    msg_id = await r.xadd(stream, {"payload": json.dumps(data)}, maxlen=maxlen, approximate=True)
    return msg_id
