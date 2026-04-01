"""Meilisearch client for the Content service."""

from meilisearch_python_sdk import AsyncClient
from meilisearch_python_sdk.models.settings import MeilisearchSettings

from shared.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

THREADS_INDEX = "threads"
_client: AsyncClient | None = None


async def connect_meili() -> AsyncClient:
    global _client
    _client = AsyncClient(url=settings.MEILI_URL, api_key=settings.MEILI_MASTER_KEY)

    await _client.create_index(THREADS_INDEX, primary_key="id")
    index = _client.index(THREADS_INDEX)

    await index.update_settings(
        MeilisearchSettings(
            searchable_attributes=["title", "description", "tags", "author_username"],
            filterable_attributes=["is_deleted", "is_pinned", "is_locked", "tags"],
            sortable_attributes=["created_at", "like_count", "hot_score"],
            ranking_rules=["words", "typo", "proximity", "attribute", "sort", "exactness"],
        )
    )
    logger.info("meilisearch_connected")
    return _client


async def disconnect_meili() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_meili() -> AsyncClient:
    if _client is None:
        raise RuntimeError("Meilisearch not connected")
    return _client
