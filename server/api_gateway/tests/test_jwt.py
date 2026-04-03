"""JWT extraction unit tests — verifies claim parsing from cookies and headers."""

from starlette.requests import Request

from main import _extract_user_claims
from shared.security import create_access_token
from .helpers import settings


def _make_request(headers):
    """Build a minimal Starlette Request with the given raw headers."""
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/v1/threads",
        "headers": headers,
    })


def _make_token():
    return create_access_token(
        subject="11111111-1111-1111-1111-111111111111",
        role="admin",
        username="testadmin",
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


class TestJWTExtraction:
    def test_valid_token_via_cookie(self):
        token = _make_token()
        claims = _extract_user_claims(
            _make_request([(b"cookie", f"access_token={token}".encode())]))
        assert claims["X-User-ID"] == "11111111-1111-1111-1111-111111111111"
        assert claims["X-User-Role"] == "admin"
        assert claims["X-User-Username"] == "testadmin"

    def test_valid_token_via_bearer(self):
        token = _make_token()
        claims = _extract_user_claims(
            _make_request([(b"authorization", f"Bearer {token}".encode())]))
        assert claims["X-User-ID"] == "11111111-1111-1111-1111-111111111111"
        assert claims["X-User-Role"] == "admin"
        assert claims["X-User-Username"] == "testadmin"

    def test_no_token(self):
        claims = _extract_user_claims(_make_request([]))
        assert claims == {}

    def test_invalid_token(self):
        claims = _extract_user_claims(
            _make_request([(b"authorization", b"Bearer invalid.token.here")]))
        assert claims == {}
