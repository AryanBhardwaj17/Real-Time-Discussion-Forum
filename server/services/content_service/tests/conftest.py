"""Shared fixtures for content service tests."""

import uuid
import pytest
import httpx

BASE = "http://localhost:8002"

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE) as c:
        yield c


@pytest.fixture
def unique():
    return uuid.uuid4().hex[:8]
