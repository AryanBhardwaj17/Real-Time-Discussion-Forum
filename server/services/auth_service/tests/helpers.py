"""Shared test helpers for auth service — importable by all test modules."""

import json
import base64


async def register_user(client, unique):
    """Register a test user and return the response JSON."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": f"t_{unique}@example.com",
        "username": f"u_{unique}",
        "password": "StrongPass1!",
    })
    return resp.json()


async def login_user(client, unique):
    """Login a test user and return the response JSON (tokens)."""
    resp = await client.post("/api/v1/auth/login", json={
        "login": f"u_{unique}", "password": "StrongPass1!",
    })
    return resp.json()


def user_id_from_jwt(tokens):
    """Extract user ID from access token payload."""
    payload_b64 = tokens["access_token"].split(".")[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))["sub"]


def auth_headers(user_id, role="member"):
    """Build fake gateway-injected auth headers."""
    return {"X-User-ID": user_id, "X-User-Role": role}
