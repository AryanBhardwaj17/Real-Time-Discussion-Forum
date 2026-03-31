"""Redis client for the Auth service — used for publishing events."""

import json

import redis.asyncio as aioredis

from shared.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

_redis: aioredis.Redis | None = None


async def connect_redis() -> aioredis.Redis:
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True, max_connections=10)
    await _redis.ping()
    logger.info("redis_connected")
    return _redis


async def disconnect_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("redis_disconnected")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not connected")
    return _redis


async def stream_add(stream: str, data: dict, maxlen: int = 10000) -> str:
    """Append a message to a Redis Stream for durable delivery."""
    r = get_redis()
    msg_id = await r.xadd(stream, {"payload": json.dumps(data)}, maxlen=maxlen, approximate=True)
    return msg_id


async def publish(channel: str, data: dict) -> None:
    """Publish a message to a Redis Pub/Sub channel for real-time delivery."""
    r = get_redis()
    await r.publish(channel, json.dumps(data))
