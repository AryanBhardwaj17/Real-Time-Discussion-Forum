"""Search microservice — queries Meilisearch for full-text thread search.

This service has NO database. It reads directly from Meilisearch.
The Content service is responsible for indexing threads into Meilisearch.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query as Q
from meilisearch_python_sdk import AsyncClient

from shared.logging import setup_logging, get_logger
from shared.exception_handlers import register_exception_handlers
from shared.middleware import RequestIDMiddleware
from shared.schemas import CursorPage

from app.config import get_settings
from app.schemas import ThreadSearchResult

settings = get_settings()
logger = get_logger(__name__)

_client: AsyncClient | None = None
THREADS_INDEX = "threads"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _client
    setup_logging(json_logs=not settings.DEBUG, log_level="DEBUG" if settings.DEBUG else "INFO", service_name="search")
    logger.info("search_service_startup")

    _client = AsyncClient(url=settings.MEILI_URL, api_key=settings.MEILI_MASTER_KEY)
    yield

    if _client:
        await _client.aclose()
        _client = None
    logger.info("search_service_shutdown")


app = FastAPI(title="Search Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "search"}


@app.get("/api/v1/search/threads", response_model=CursorPage[ThreadSearchResult])
async def search_threads(
    q: str = Q(..., min_length=1, max_length=200),
    cursor: str | None = Q(None),
    limit: int = Q(20, ge=1, le=100),
) -> CursorPage[ThreadSearchResult]:
    """Full-text search over threads using Meilisearch."""
    q = q.strip()
    if not q:
        return CursorPage(items=[], next_cursor=None, has_more=False)

    offset = 0
    if cursor and cursor.startswith("offset:"):
        try:
            offset = int(cursor.removeprefix("offset:"))
        except ValueError:
            offset = 0

    if _client is None:
        raise HTTPException(status_code=503, detail="Search service not initialized")
    index = _client.index(THREADS_INDEX)

    try:
        results = await index.search(
            q, offset=offset, limit=limit + 1,
            filter="is_deleted = false",
            attributes_to_retrieve=[
                "id", "title", "description", "author_id", "author_username",
                "tags", "like_count", "comment_count", "hot_score",
                "is_pinned", "is_locked", "created_at",
            ],
        )
    except Exception:
        logger.exception("search_failed", query=q)
        raise HTTPException(status_code=503, detail="Search temporarily unavailable")

    hits = results.hits or []
    next_cursor = None
    if len(hits) > limit:
        hits = hits[:limit]
        next_cursor = f"offset:{offset + limit}"

    return CursorPage(
        items=[ThreadSearchResult(**hit) for hit in hits],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )
