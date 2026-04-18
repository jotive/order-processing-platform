from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_env: str = Field(default="local")
    api_log_level: str = Field(default="INFO")
    api_port: int = Field(default=8000)

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/orders"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    secret_key: str = Field(default="change-me-in-production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
