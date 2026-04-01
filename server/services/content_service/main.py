"""Content microservice — threads, comments, likes, reports."""

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

USER_UPDATES_STREAM = "stream:user_updates"
USER_UPDATES_GROUP = "content-service"
USER_UPDATES_CONSUMER = "worker-1"

MEILI_STREAM = "stream:meili_indexing"
MEILI_GROUP = "content-meili-worker"
MEILI_CONSUMER = "worker-1"
MEILI_DLQ = "stream:meili_indexing:dead"
MAX_MEILI_RETRIES = 3

RECONCILE_INTERVAL_SECONDS = 600  # 10 minutes


async def _seed_report_reasons() -> None:
    """Ensure report_reasons lookup table has default entries."""
    from app.db import async_session_factory
    from app.models import ReportReasonLookup
    from sqlalchemy import select

    defaults = [
        ("spam", "Spam or misleading"),
        ("harassment", "Harassment or bullying"),
        ("inappropriate", "Inappropriate content"),
        ("other", "Other"),
    ]
    async with async_session_factory() as session:
        for code, label in defaults:
            exists = await session.execute(select(ReportReasonLookup).where(ReportReasonLookup.code == code))
            if exists.scalar_one_or_none() is None:
                session.add(ReportReasonLookup(code=code, label=label))
        await session.commit()
    logger.info("report_reasons_seeded")


async def _seed_report_statuses() -> None:
    """Ensure report_statuses lookup table has default entries."""
    from app.db import async_session_factory
    from app.models import ReportStatusLookup
    from sqlalchemy import select

    defaults = [
        ("pending", "Pending review"),
        ("approved", "Approved — action taken"),
        ("rejected", "Rejected — no action"),
        ("resolved", "Resolved — action taken"),
        ("dismissed", "Dismissed — no action needed"),
        ("archived", "Archived"),
    ]
    async with async_session_factory() as session:
        for code, label in defaults:
            exists = await session.execute(select(ReportStatusLookup).where(ReportStatusLookup.code == code))
            if exists.scalar_one_or_none() is None:
                session.add(ReportStatusLookup(code=code, label=label))
        await session.commit()
    logger.info("report_statuses_seeded")


_user_updates_task = None
_reconcile_task = None
_meili_worker_task = None


async def _ensure_user_updates_group(r) -> None:
    """Create the consumer group if it doesn't already exist."""
    try:
        await r.xgroup_create(USER_UPDATES_STREAM, USER_UPDATES_GROUP, id="0", mkstream=True)
        logger.info("consumer_group_created", stream=USER_UPDATES_STREAM, group=USER_UPDATES_GROUP)
    except Exception as e:
        if "BUSYGROUP" in str(e):
            pass
        else:
            raise


async def _user_updates_listener() -> None:
    """Listen for user profile changes (e.g. username) and update denormalized copies."""
    import redis.asyncio as aioredis
    from sqlalchemy import update as sa_update
    from app.db import async_session_factory
    from app.models import Thread, Comment

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await _ensure_user_updates_group(r)
    logger.info("user_updates_listener_started")

    try:
        # Phase 1: Drain pending messages from a prior crash
        while True:
            pending = await r.xreadgroup(
                USER_UPDATES_GROUP, USER_UPDATES_CONSUMER,
                {USER_UPDATES_STREAM: "0"}, count=10,
            )
            if not pending or not pending[0][1]:
                break
            for _stream_name, entries in pending:
                for msg_id, fields in entries:
                    try:
                        data = json.loads(fields["payload"])
                        if data.get("event") == "username_changed":
                            user_id = data["user_id"]
                            new_username = data["new_username"]
                            async with async_session_factory() as session:
                                await session.execute(
                                    sa_update(Thread)
                                    .where(Thread.author_id == user_id)
                                    .values(author_username=new_username)
                                )
                                await session.execute(
                                    sa_update(Comment)
                                    .where(Comment.author_id == user_id)
                                    .values(author_username=new_username)
                                )
                                await session.commit()
                            logger.info("pending_username_propagated", user_id=user_id, new_username=new_username)
                        elif data.get("event") == "user_status_changed":
                            user_id = data["user_id"]
                            is_active = data["is_active"]
                            async with async_session_factory() as session:
                                await session.execute(
                                    sa_update(Thread)
                                    .where(Thread.author_id == user_id)
                                    .values(author_is_active=is_active)
                                )
                                await session.execute(
                                    sa_update(Comment)
                                    .where(Comment.author_id == user_id)
                                    .values(author_is_active=is_active)
                                )
                                await session.commit()
                            logger.info("pending_user_status_propagated", user_id=user_id, is_active=is_active)
                        await r.xack(USER_UPDATES_STREAM, USER_UPDATES_GROUP, msg_id)
                    except Exception:
                        logger.exception("pending_user_updates_error", msg_id=msg_id)
                        await r.xack(USER_UPDATES_STREAM, USER_UPDATES_GROUP, msg_id)
        logger.info("pending_user_updates_drained")

        # Phase 2: Process new messages
        while True:
            messages = await r.xreadgroup(
                USER_UPDATES_GROUP, USER_UPDATES_CONSUMER,
                {USER_UPDATES_STREAM: ">"}, count=10, block=5000,
            )
            if not messages:
                continue

            for _stream_name, entries in messages:
                for msg_id, fields in entries:
                    try:
                        data = json.loads(fields["payload"])
                        if data.get("event") == "username_changed":
                            user_id = data["user_id"]
                            new_username = data["new_username"]
                            async with async_session_factory() as session:
                                await session.execute(
                                    sa_update(Thread)
                                    .where(Thread.author_id == user_id)
                                    .values(author_username=new_username)
                                )
                                await session.execute(
                                    sa_update(Comment)
                                    .where(Comment.author_id == user_id)
                                    .values(author_username=new_username)
                                )
                                await session.commit()
                            logger.info("username_propagated", user_id=user_id, new_username=new_username)

                        elif data.get("event") == "user_status_changed":
                            user_id = data["user_id"]
                            is_active = data["is_active"]
                            async with async_session_factory() as session:
                                await session.execute(
                                    sa_update(Thread)
                                    .where(Thread.author_id == user_id)
                                    .values(author_is_active=is_active)
                                )
                                await session.execute(
                                    sa_update(Comment)
                                    .where(Comment.author_id == user_id)
                                    .values(author_is_active=is_active)
                                )
                                await session.commit()
                            logger.info("user_status_propagated", user_id=user_id, is_active=is_active)

                        await r.xack(USER_UPDATES_STREAM, USER_UPDATES_GROUP, msg_id)
                    except Exception:
                        logger.exception("user_updates_listener_error", msg_id=msg_id)
    except asyncio.CancelledError:
        pass
    finally:
        await r.aclose()


async def _periodic_counter_reconciliation() -> None:
    """Periodically reconcile denormalized counters against actual row counts."""
    from app.db import async_session_factory
    from app.services import reconcile_counters

    # Wait a bit on startup before first run
    await asyncio.sleep(60)

    try:
        while True:
            try:
                async with async_session_factory() as session:
                    fixed = await reconcile_counters(session)
                    await session.commit()
                    total = sum(fixed.values())
                    if total > 0:
                        logger.info("counter_reconciliation_complete", fixed=fixed)
            except Exception:
                logger.exception("counter_reconciliation_error")
            await asyncio.sleep(RECONCILE_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        pass


async def _meili_indexing_worker() -> None:
    """Background worker: processes Meilisearch indexing tasks from Redis Stream."""
    import redis.asyncio as aioredis
    from app.core.meilisearch import get_meili, THREADS_INDEX

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        await r.xgroup_create(MEILI_STREAM, MEILI_GROUP, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise

    logger.info("meili_indexing_worker_started")

    try:
        # Phase 1: Drain pending messages from a prior crash
        while True:
            pending = await r.xreadgroup(
                MEILI_GROUP, MEILI_CONSUMER, {MEILI_STREAM: "0"}, count=10,
            )
            if not pending or not pending[0][1]:
                break
            for _stream, entries in pending:
                for msg_id, fields in entries:
                    try:
                        data = json.loads(fields["payload"])
                        action = data.get("action")
                        client = get_meili()
                        index = client.index(THREADS_INDEX)

                        if action == "index":
                            doc = json.loads(data["doc"])
                            await index.add_documents([doc])
                        elif action == "delete":
                            await index.delete_document(data["thread_id"])
                        elif action == "update":
                            doc = json.loads(data["doc"])
                            await index.update_documents([doc])

                        await r.xack(MEILI_STREAM, MEILI_GROUP, msg_id)
                    except Exception:
                        logger.exception("pending_meili_error", msg_id=msg_id)
                        await r.xack(MEILI_STREAM, MEILI_GROUP, msg_id)
        logger.info("pending_meili_tasks_drained")

        # Phase 2: Process new messages
        while True:
            messages = await r.xreadgroup(
                MEILI_GROUP, MEILI_CONSUMER, {MEILI_STREAM: ">"}, count=10, block=5000,
            )
            if not messages:
                continue

            for _stream, entries in messages:
                for msg_id, fields in entries:
                    try:
                        data = json.loads(fields["payload"])
                        action = data.get("action")
                        client = get_meili()
                        index = client.index(THREADS_INDEX)

                        if action == "index":
                            doc = json.loads(data["doc"])
                            await index.add_documents([doc])
                        elif action == "delete":
                            await index.delete_document(data["thread_id"])
                        elif action == "update":
                            doc = json.loads(data["doc"])
                            await index.update_documents([doc])

                        await r.xack(MEILI_STREAM, MEILI_GROUP, msg_id)
                    except Exception:
                        logger.exception("meili_worker_error", msg_id=msg_id)
                        try:
                            retry_key = f"meili:retries:{msg_id}"
                            retry_count = int(await r.hincrby(retry_key, "count", 1))
                            if retry_count >= MAX_MEILI_RETRIES:
                                await r.xadd(MEILI_DLQ, fields, maxlen=10000, approximate=True)
                                await r.xack(MEILI_STREAM, MEILI_GROUP, msg_id)
                                await r.delete(retry_key)
                                logger.warning("meili_task_moved_to_dlq", msg_id=msg_id)
                        except Exception:
                            logger.exception("meili_dlq_error", msg_id=msg_id)
    except asyncio.CancelledError:
        pass
    finally:
        await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _user_updates_task, _reconcile_task, _meili_worker_task
    setup_logging(json_logs=not settings.DEBUG, log_level="DEBUG" if settings.DEBUG else "INFO", service_name="content")
    logger.info("content_service_startup")

    await create_tables()
    await _seed_report_reasons()
    await _seed_report_statuses()

    from app.core.redis import connect_redis, disconnect_redis
    from app.core.meilisearch import connect_meili, disconnect_meili

    await connect_redis()
    await connect_meili()

    _user_updates_task = asyncio.create_task(_user_updates_listener())
    _reconcile_task = asyncio.create_task(_periodic_counter_reconciliation())
    _meili_worker_task = asyncio.create_task(_meili_indexing_worker())

    yield

    for task in (_user_updates_task, _reconcile_task, _meili_worker_task):
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    await disconnect_meili()
    await disconnect_redis()
    await engine.dispose()
    logger.info("content_service_shutdown")


app = FastAPI(title="Content Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "content"}


from app.routes import threads_router, comments_router, reports_router, internal_router, profile_router

app.include_router(threads_router, prefix="/api/v1")
app.include_router(comments_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(internal_router)
