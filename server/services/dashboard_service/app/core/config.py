from functools import lru_cache
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
    DEBUG: bool = False
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    AUTH_SERVICE_URL: str = "http://auth:8001"
    CONTENT_SERVICE_URL: str = "http://content:8002"
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
