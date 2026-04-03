"""API Gateway — reverse proxy with JWT validation, rate limiting, and CORS.

All client traffic enters here. The gateway:
1. Validates JWT tokens (stateless — no DB lookup)
2. Injects X-User-ID, X-User-Role, X-User-Username headers
3. Proxies requests to the appropriate backend microservice
4. Handles rate limiting and CORS centrally
5. Manages HttpOnly cookie-based JWT storage (secure token handling)
"""

import json
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import httpx
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from shared.logging import setup_logging, get_logger
from shared.middleware import RequestIDMiddleware
from shared.security import decode_access_token

from app.config import get_settings

settings = get_settings()
logger = get_logger(__name__)

# ── Request Body Size Limit ──────────────────────────────────────────
MAX_BODY_SIZE = 10_485_760  # 10 MB

# ── Per-Backend Timeout (seconds) ────────────────────────────────────
TIMEOUT_MAP: list[tuple[str, float]] = [
    ("/api/v1/search", 5.0),
    ("/api/v1/auth", 10.0),
    ("/api/v1/notifications", 10.0),
    ("/api/v1/threads", 15.0),
    ("/api/v1/comments", 15.0),
    ("/api/v1/dashboard", 15.0),
]
DEFAULT_TIMEOUT = 15.0


def _resolve_timeout(path: str) -> float:
    """Return the per-route timeout for a given request path."""
    for prefix, timeout in TIMEOUT_MAP:
        if path.startswith(prefix):
            return timeout
    return DEFAULT_TIMEOUT


def _check_body_size(request: Request) -> Response | None:
    """Reject requests whose Content-Length exceeds MAX_BODY_SIZE."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_BODY_SIZE:
                return Response(
                    content='{"detail":"Request body too large"}',
                    status_code=413,
                    media_type="application/json",
                )
        except ValueError:
            pass
    return None

# ── Async HTTP client for proxying ───────────────────────────────────
_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _http_client
    setup_logging(json_logs=not settings.DEBUG, log_level="DEBUG" if settings.DEBUG else "INFO", service_name="gateway")
    logger.info("gateway_startup", version="0.1.0")

    _http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    yield

    await _http_client.aclose()
    _http_client = None
    logger.info("gateway_shutdown")


app = FastAPI(title="Forum API Gateway", version="0.1.0", lifespan=lifespan)

# ── Rate Limiter ─────────────────────────────────────────────────────
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ───────────────────────────────────────────────────────
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Route Map: prefix → backend service URL ─────────────────────────
ROUTE_MAP: list[tuple[str, str]] = [
    ("/api/v1/auth", settings.AUTH_SERVICE_URL),
    ("/api/v1/users", settings.AUTH_SERVICE_URL),
    ("/api/v1/admin", settings.AUTH_SERVICE_URL),
    ("/api/v1/threads", settings.CONTENT_SERVICE_URL),
    ("/api/v1/comments", settings.CONTENT_SERVICE_URL),
    ("/api/v1/reports", settings.CONTENT_SERVICE_URL),
    ("/api/v1/profiles", settings.CONTENT_SERVICE_URL),
    ("/api/v1/notifications", settings.NOTIFICATION_SERVICE_URL),
    ("/api/v1/search", settings.SEARCH_SERVICE_URL),
    ("/api/v1/dashboard", settings.DASHBOARD_SERVICE_URL),
]


def _resolve_backend(path: str) -> str | None:
    """Find the backend service URL for a given request path."""
    for prefix, url in ROUTE_MAP:
        if path.startswith(prefix):
            return url
    return None


# ── Cookie Settings ──────────────────────────────────────────────────
COOKIE_SECURE = not settings.DEBUG          # Secure flag (HTTPS only in prod)
COOKIE_SAMESITE = "lax"                     # Prevents CSRF on cross-origin GETs
COOKIE_HTTPONLY = True                      # JS cannot read these cookies
COOKIE_PATH = "/"
ACCESS_TOKEN_MAX_AGE = 15 * 60              # 15 minutes
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60   # 7 days


def _set_token_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HttpOnly cookies for both tokens on the response."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=ACCESS_TOKEN_MAX_AGE,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/api/v1/auth",   # only sent to auth endpoints
        max_age=REFRESH_TOKEN_MAX_AGE,
    )


def _clear_token_cookies(response: Response) -> None:
    """Delete both token cookies."""
    response.delete_cookie(key="access_token", path=COOKIE_PATH)
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")


def _get_access_token(request: Request) -> str | None:
    """Read access token from cookie (primary) or Authorization header (fallback)."""
    token = request.cookies.get("access_token")
    if token:
        return token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ")
    return None


def _extract_user_claims(request: Request) -> dict[str, str]:
    """Extract user claims from cookie or Authorization header."""
    token = _get_access_token(request)
    if not token:
        return {}

    payload = decode_access_token(token, secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    if payload is None:
        return {}

    return {
        "X-User-ID": payload.get("sub", ""),
        "X-User-Role": payload.get("role", "member"),
        "X-User-Username": payload.get("username", ""),
    }


# ── Health Check ─────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "gateway"}


# Token endpoints whose responses contain tokens to set as cookies
TOKEN_ENDPOINTS = {"/api/v1/auth/login", "/api/v1/auth/refresh"}


async def _proxy_to_backend(request: Request, full_path: str) -> httpx.Response:
    """Send request to the appropriate backend service and return raw response."""
    backend_url = _resolve_backend(full_path)
    if backend_url is None:
        return httpx.Response(status_code=404, json={"detail": "Route not found"})
    target = f"{backend_url}{full_path}"
    if request.url.query:
        target += f"?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)

    # SECURITY: Always strip client-supplied identity headers to prevent
    # spoofing. These are only set by the gateway from validated JWT claims.
    for hdr in ("X-User-ID", "X-User-Role", "X-User-Username",
                "x-user-id", "x-user-role", "x-user-username"):
        headers.pop(hdr, None)

    headers.update(_extract_user_claims(request))
    headers["X-Request-ID"] = getattr(request.state, "request_id", "")

    # For refresh endpoint, inject refresh_token from cookie into the JSON body
    body = await request.body()
    if full_path == "/api/v1/auth/refresh":
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            return httpx.Response(status_code=401, json={"detail": "No refresh token"})
        body = json.dumps({"refresh_token": refresh_token}).encode()
        headers["content-type"] = "application/json"
        headers["content-length"] = str(len(body))

    # For logout endpoint, inject refresh_token from cookie into the JSON body
    if full_path == "/api/v1/auth/logout":
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            body = json.dumps({"refresh_token": refresh_token}).encode()
            headers["content-type"] = "application/json"
            headers["content-length"] = str(len(body))

    if _http_client is None:
        return httpx.Response(status_code=503, json={"detail": "Service unavailable"})
    timeout = _resolve_timeout(full_path)
    return await _http_client.request(
        method=request.method, url=target, headers=headers, content=body,
        timeout=timeout,
    )


def _build_response(backend_response: httpx.Response, request_path: str) -> Response:
    """Build gateway response, setting/clearing cookies for auth endpoints."""
    response_headers = {
        k: v for k, v in backend_response.headers.items()
        if k.lower() not in ("transfer-encoding", "connection", "content-encoding", "content-length", "set-cookie")
    }

    # For token endpoints with successful responses, set HttpOnly cookies
    if request_path in TOKEN_ENDPOINTS and backend_response.status_code == 200:
        try:
            data = backend_response.json()
            access_token = data.get("access_token", "")
            refresh_token = data.get("refresh_token", "")

            # Return response without tokens in JSON body (they go in cookies)
            safe_body = json.dumps({"message": "Authenticated successfully"})
            response = Response(
                content=safe_body,
                status_code=200,
                headers=response_headers,
                media_type="application/json",
            )
            _set_token_cookies(response, access_token, refresh_token)
            return response
        except Exception:
            pass  # Fall through to default response

    # For logout, clear cookies
    if request_path == "/api/v1/auth/logout":
        response = Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=response_headers,
            media_type=backend_response.headers.get("content-type"),
        )
        _clear_token_cookies(response)
        return response

    # For failed refresh, clear stale cookies so the browser stops retrying
    if request_path == "/api/v1/auth/refresh" and backend_response.status_code != 200:
        response = Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=response_headers,
            media_type=backend_response.headers.get("content-type"),
        )
        _clear_token_cookies(response)
        return response

    return Response(
        content=backend_response.content,
        status_code=backend_response.status_code,
        headers=response_headers,
        media_type=backend_response.headers.get("content-type"),
    )


# ── Reverse Proxy: HTTP ──────────────────────────────────────────────
@app.api_route("/api/v1/auth/login", methods=["POST"])
@app.api_route("/api/v1/auth/register", methods=["POST"])
@limiter.limit("10/minute")
async def proxy_auth_sensitive(request: Request) -> Response:
    """Rate-limited proxy for sensitive auth endpoints."""
    if (size_error := _check_body_size(request)):
        return size_error
    full_path = request.url.path
    backend_response = await _proxy_to_backend(request, full_path)
    return _build_response(backend_response, full_path)


@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@limiter.limit("60/minute")
async def proxy(request: Request, path: str) -> Response:
    """Proxy all /api/v1/* requests to the appropriate backend service."""
    if (size_error := _check_body_size(request)):
        return size_error
    full_path = f"/api/v1/{path}"
    backend_url = _resolve_backend(full_path)

    if backend_url is None:
        return Response(content='{"detail":"Route not found"}', status_code=404, media_type="application/json")

    backend_response = await _proxy_to_backend(request, full_path)
    return _build_response(backend_response, full_path)


# ── Reverse Proxy: WebSocket ────────────────────────────────────────
@app.websocket("/ws/{path:path}")
async def ws_proxy(ws: WebSocket, path: str) -> None:
    """Proxy WebSocket connections to the Realtime service.

    The gateway injects an auth handshake message on behalf of the client
    using the HttpOnly cookie. This keeps the JWT out of JS-accessible scope
    while still authenticating the WebSocket with the backend.
    """
    await ws.accept()

    target = f"{settings.REALTIME_SERVICE_URL}/ws/{path}"
    # Replace http(s) with ws(s) for the WebSocket connection
    target = target.replace("http://", "ws://").replace("https://", "wss://")

    import websockets

    try:
        async with websockets.connect(target) as backend_ws:
            import asyncio

            # Inject auth handshake: read cookie and send auth message to backend
            token = ws.cookies.get("access_token")
            if token:
                await backend_ws.send(json.dumps({"type": "auth", "token": token}))

            async def client_to_backend() -> None:
                try:
                    while True:
                        data = await ws.receive_text()
                        await backend_ws.send(data)
                except WebSocketDisconnect:
                    await backend_ws.close()

            async def backend_to_client() -> None:
                try:
                    async for message in backend_ws:
                        if isinstance(message, str):
                            await ws.send_text(message)
                        else:
                            await ws.send_bytes(message)
                except Exception:
                    pass

            await asyncio.gather(client_to_backend(), backend_to_client())
    except Exception:
        logger.exception("ws_proxy_error", path=path)
    finally:
        try:
            await ws.close()
        except Exception:
            pass
