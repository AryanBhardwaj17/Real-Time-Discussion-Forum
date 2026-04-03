"""Route resolution unit tests — pure function, no network."""

from main import _resolve_backend
from .helpers import settings


class TestRouteResolution:
    def test_auth_route(self):
        assert _resolve_backend("/api/v1/auth/login") == settings.AUTH_SERVICE_URL

    def test_users_route(self):
        assert _resolve_backend("/api/v1/users/me") == settings.AUTH_SERVICE_URL

    def test_admin_route(self):
        assert _resolve_backend("/api/v1/admin/users") == settings.AUTH_SERVICE_URL

    def test_threads_route(self):
        assert _resolve_backend("/api/v1/threads") == settings.CONTENT_SERVICE_URL

    def test_comments_route(self):
        assert _resolve_backend("/api/v1/comments/123") == settings.CONTENT_SERVICE_URL

    def test_notifications_route(self):
        assert _resolve_backend("/api/v1/notifications") == settings.NOTIFICATION_SERVICE_URL

    def test_search_route(self):
        assert _resolve_backend("/api/v1/search/threads") == settings.SEARCH_SERVICE_URL

    def test_dashboard_route(self):
        assert _resolve_backend("/api/v1/dashboard/admin/stats") == settings.DASHBOARD_SERVICE_URL

    def test_unknown_route(self):
        assert _resolve_backend("/api/v1/unknown") is None
