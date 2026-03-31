"""Auth service configuration."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    DEBUG: bool = False

    # ── Security ─────────────────────────────────────────────────
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Default Admin ────────────────────────────────────────────
    DEFAULT_ADMIN_EMAIL: str = "admin@forum.dev"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str  # Required — must be set via environment variable

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── Internal ─────────────────────────────────────────────────
    INTERNAL_SECRET: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_async_db_url(cls, v: Any) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
