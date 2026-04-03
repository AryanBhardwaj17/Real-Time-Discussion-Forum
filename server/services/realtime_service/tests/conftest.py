"""Shared fixtures for realtime service tests."""

import pytest
import httpx

BASE = "http://localhost:8006"

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE) as c:
        yield c
