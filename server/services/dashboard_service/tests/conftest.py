"""Shared fixtures for dashboard service tests."""

import pytest
import httpx

BASE = "http://localhost:8005"

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE) as c:
        yield c
