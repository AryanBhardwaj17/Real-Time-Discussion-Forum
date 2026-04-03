"""Gateway configuration — service URLs and security settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings configuration using Pydantic BaseSettings.
    This class manages all configuration variables for the gateway service,
    loading them from environment variables via a .env file.
    Attributes:
        DEBUG (bool): Enable debug mode. Defaults to False.
        SECRET_KEY (str): Secret key for JWT token signing. Required.
        ALGORITHM (str): JWT algorithm for token creation. Defaults to "HS256".
        CORS_ORIGINS (list[str]): List of allowed CORS origins for frontend requests.
            Configured for multiple localhost ports (5173-5180) to support development
            of multiple frontend applications or micro-frontend instances simultaneously.
        AUTH_SERVICE_URL (str): Internal URL for authentication service.
        CONTENT_SERVICE_URL (str): Internal URL for content service.
        NOTIFICATION_SERVICE_URL (str): Internal URL for notification service.
        SEARCH_SERVICE_URL (str): Internal URL for search service.
        DASHBOARD_SERVICE_URL (str): Internal URL for dashboard service.
        REALTIME_SERVICE_URL (str): Internal URL for real-time service.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    DEBUG: bool = False

    # ── Security ─────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177", "http://localhost:5178", "http://localhost:5179", "http://localhost:5180"]

    # ── Backend Service URLs ─────────────────────────────────────
    AUTH_SERVICE_URL: str = "http://auth:8001"
    CONTENT_SERVICE_URL: str = "http://content:8002"
    NOTIFICATION_SERVICE_URL: str = "http://notification:8003"
    SEARCH_SERVICE_URL: str = "http://search:8004"
    DASHBOARD_SERVICE_URL: str = "http://dashboard:8005"
    REALTIME_SERVICE_URL: str = "http://realtime:8006"


@lru_cache
def get_settings() -> Settings:
    return Settings()
