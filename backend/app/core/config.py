"""Single source of environment configuration for the whole backend.

Reads the .env locally and real environment variables in deploy, validating both
once at startup so a missing or malformed variable fails on boot, not mid-request.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The .env lives at the repo root, not in backend/, since docker compose and the
# frontend read it too. app/core/config.py -> app/ -> backend/ -> repo root.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Environment configuration, read and validated once per process.

    Fields without a default are required: a missing variable fails at import
    time with the variable name, instead of surfacing as a None deep inside a
    request handler.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        # The .env is shared with docker compose and the frontend, so it holds
        # keys this class does not declare. Without this, those raise on boot.
        extra="ignore",
    )

    database_url: str

    # Only pytest needs it: the app has to boot on a machine that never runs tests.
    test_database_url: str | None = None

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Comma-separated rather than list[str]: pydantic-settings parses complex
    # types as JSON, so a list field would reject "http://a,http://b".
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env is parsed once, not on every call or request."""
    return Settings()
