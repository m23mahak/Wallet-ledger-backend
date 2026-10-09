"""Environment-driven settings. Nothing secret is hardcoded here."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "WalletLedger"
    environment: str = "development"
    debug: bool = False

    database_url: str  # required, no default on purpose
    db_echo: bool = False

    jwt_secret: str  # required
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    default_currency: str = "INR"
    cors_origins: str = ""  # comma-separated
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url")
    @classmethod
    def require_asyncpg(cls, v: str) -> str:
        if not (v.startswith("postgresql+asyncpg://") or v.startswith("sqlite+aiosqlite://")):
            raise ValueError("DATABASE_URL must start with postgresql+asyncpg:// or sqlite+aiosqlite://")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
