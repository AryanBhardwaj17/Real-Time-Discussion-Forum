"""Dashboard microservice — aggregated stats, audit log, activity feeds.

Consumes audit events from Redis Streams and stores them locally.
Calls Auth and Content services for aggregated stats.
"""

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

STREAM = "stream:audit"
GROUP = "dashboard-service"
CONSUMER = "worker-1"
DLQ_STREAM = "stream:audit:dead"
MAX_RETRIES = 3

_listener_task = None


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


async def _audit_listener() -> None:
    """Read from Redis Stream and store audit logs in local DB."""
    import redis.asyncio as aioredis
    from app.db import async_session_factory
    from app.models import AuditLog

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await _ensure_consumer_group(r)
    logger.info("audit_stream_listener_started")

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
                        async with async_session_factory() as session:
                            entry = AuditLog(
                                actor_id=data["actor_id"],
                                action=data["action"],
                                target_type=data["target_type"],
                                target_id=data["target_id"],
                                details=data.get("details"),
                            )
                            session.add(entry)
                            await session.commit()
                        await r.xack(STREAM, GROUP, msg_id)
                    except Exception:
                        logger.exception("pending_audit_error", msg_id=msg_id)
                        await r.xack(STREAM, GROUP, msg_id)
        logger.info("pending_audit_events_drained")

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
                        async with async_session_factory() as session:
                            entry = AuditLog(
                                actor_id=data["actor_id"],
                                action=data["action"],
                                target_type=data["target_type"],
                                target_id=data["target_id"],
                                details=data.get("details"),
                            )
                            session.add(entry)
                            await session.commit()

                        # Acknowledge after successful DB commit
                        await r.xack(STREAM, GROUP, msg_id)
                    except Exception:
                        logger.exception("audit_listener_error", msg_id=msg_id)
                        try:
                            retry_key = f"audit:retries:{msg_id}"
                            retry_count = int(await r.hincrby(retry_key, "count", 1))
                            if retry_count >= MAX_RETRIES:
                                await r.xadd(DLQ_STREAM, fields, maxlen=10000, approximate=True)
                                await r.xack(STREAM, GROUP, msg_id)
                                await r.delete(retry_key)
                                logger.warning("audit_moved_to_dlq", msg_id=msg_id, retries=retry_count)
                        except Exception:
                            logger.exception("dlq_handling_error", msg_id=msg_id)
    except asyncio.CancelledError:
        pass
    finally:
        await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _listener_task
    setup_logging(json_logs=not settings.DEBUG, log_level="DEBUG" if settings.DEBUG else "INFO", service_name="dashboard")
    logger.info("dashboard_service_startup")

    await create_tables()
    _listener_task = asyncio.create_task(_audit_listener())

    yield

    if _listener_task:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
    await engine.dispose()
    logger.info("dashboard_service_shutdown")


app = FastAPI(title="Dashboard Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "dashboard"}


from app.routes import router
app.include_router(router, prefix="/api/v1")
