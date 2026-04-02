"""Notification microservice — in-app notifications with Redis Streams consumer."""

import asyncio
import json
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from shared.logging import setup_logging, get_logger
from shared.exception_handlers import register_exception_handlers
from shared.middleware import RequestIDMiddleware

from app.core.config import get_settings
from app.db import engine, create_tables

settings = get_settings()
logger = get_logger(__name__)

STREAM = "stream:notifications"
GROUP = "notification-service"
CONSUMER = "worker-1"
DLQ_STREAM = "stream:notifications:dead"
MAX_RETRIES = 3

_listener_task = None


async def _seed_notification_types() -> None:
    """Ensure notification_types lookup table has default entries."""
    from app.db import async_session_factory
    from app.models import NotificationTypeLookup
    from sqlalchemy import select

    defaults = [
        ("reply", "Reply to your content"),
        ("mention", "Mentioned in a post"),
        ("thread_like", "Someone liked your thread"),
        ("comment_like", "Someone liked your comment"),
    ]
    async with async_session_factory() as session:
        for code, label in defaults:
            exists = await session.execute(select(NotificationTypeLookup).where(NotificationTypeLookup.code == code))
            if exists.scalar_one_or_none() is None:
                session.add(NotificationTypeLookup(code=code, label=label))
        await session.commit()
    logger.info("notification_types_seeded")



async def _ensure_consumer_group(r) -> None:
    """Create the consumer group if it doesn't already exist."""
    try:
        await r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        logger.info("consumer_group_created", stream=STREAM, group=GROUP)
    except Exception as e:
        if "BUSYGROUP" in str(e):
            pass  # Group already exists
        else:
            raise


async def _notification_listener() -> None:
    """Read from Redis Stream and store notifications in DB."""
    import redis.asyncio as aioredis
    from sqlalchemy import delete as sa_delete
    from sqlalchemy.exc import IntegrityError
    from app.db import async_session_factory
    from app.models import Notification

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await _ensure_consumer_group(r)
    logger.info("notification_stream_listener_started")

    async def _process_message(data: dict) -> None:
        """Process a single notification or retraction event."""
        if data.get("action") == "retract":
            # Delete the matching notification (e.g. user un-liked)
            async with async_session_factory() as session:
                stmt = sa_delete(Notification).where(
                    Notification.actor_id == data["actor_id"],
                    Notification.type == data["notification_type"],
                    Notification.reference_id == data["reference_id"],
                )
                result = await session.execute(stmt)
                await session.commit()
            if result.rowcount > 0 and data.get("user_id"):
                await r.publish(f"user:{data['user_id']}", json.dumps({
                    "type": "notification_retracted",
                    "data": {
                        "notification_type": data["notification_type"],
                        "reference_id": data["reference_id"],
                    },
                }))
            logger.info("notification_retracted", notification_type=data["notification_type"], reference_id=data["reference_id"])
            return

        async with async_session_factory() as session:
            notification = Notification(
                user_id=data["user_id"],
                actor_id=data["actor_id"],
                type=data["notification_type"],
                reference_type=data["reference_type"],
                reference_id=data["reference_id"],
                thread_id=data.get("thread_id"),
                content=data["content"],
            )
            session.add(notification)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info("duplicate_notification_skipped")
                return

            await r.publish(f"user:{data['user_id']}", json.dumps({
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "notification_type": data["notification_type"],
                    "reference_type": data["reference_type"],
                    "reference_id": data["reference_id"],
                    "thread_id": data.get("thread_id"),
                    "content": data["content"],
                    "created_at": notification.created_at.isoformat(),
                },
            }))

    try:
        # Phase 1: Drain pending messages from a prior crash
        while True:
            pending = await r.xreadgroup(
                GROUP, CONSUMER, {STREAM: "0"}, count=10,
            )
            if not pending or not pending[0][1]:
                break
            for _stream_name, entries in pending:
                for msg_id, fields in entries:
                    try:
                        data = json.loads(fields["payload"])
                        await _process_message(data)
                        await r.xack(STREAM, GROUP, msg_id)
                    except Exception:
                        logger.exception("pending_notification_error", msg_id=msg_id)
                        await r.xack(STREAM, GROUP, msg_id)
        logger.info("pending_notifications_drained")

        # Phase 2: Process new messages
        while True:
            messages = await r.xreadgroup(
                GROUP, CONSUMER, {STREAM: ">"}, count=10, block=5000,
            )
            if not messages:
                continue

            for _stream_name, entries in messages:
                for msg_id, fields in entries:
                    try:
                        data = json.loads(fields["payload"])
                        await _process_message(data)
                        await r.xack(STREAM, GROUP, msg_id)
                    except Exception:
                        logger.exception("notification_listener_error", msg_id=msg_id)
                        try:
                            retry_key = f"notification:retries:{msg_id}"
                            retry_count = int(await r.hincrby(retry_key, "count", 1))
                            await r.expire(retry_key, 86400)  # 24h TTL to prevent memory leak
                            if retry_count >= MAX_RETRIES:
                                await r.xadd(DLQ_STREAM, fields, maxlen=10000, approximate=True)
                                await r.xack(STREAM, GROUP, msg_id)
                                await r.delete(retry_key)
                                logger.warning("notification_moved_to_dlq", msg_id=msg_id, retries=retry_count)
                        except Exception:
                            logger.exception("dlq_handling_error", msg_id=msg_id)
    except asyncio.CancelledError:
        pass
    finally:
        await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _listener_task
    setup_logging(json_logs=not settings.DEBUG, log_level="DEBUG" if settings.DEBUG else "INFO", service_name="notification")
    logger.info("notification_service_startup")

    await create_tables()
    await _seed_notification_types()
    _listener_task = asyncio.create_task(_notification_listener())

    yield

    if _listener_task:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()
    logger.info("notification_service_shutdown")


app = FastAPI(title="Notification Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "notification"}


from app.routes import router
app.include_router(router, prefix="/api/v1")
