from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
    DEBUG: bool = False
    MEILI_URL: str = "http://meilisearch:7700"
    MEILI_MASTER_KEY: str = "forum_meili_master_key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
