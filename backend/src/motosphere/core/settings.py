"""Typed, validated and immutable backend settings.

Settings come from environment variables with the ``MOTOSPHERE_`` prefix and
from an optional ``.env`` file in the current working directory (``backend/``
for every backend command). Real environment variables take precedence over
the file. Any unknown key in the file is rejected, so a misspelt setting fails
loudly instead of being silently ignored.

Application code obtains settings through :func:`get_settings`.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["ENV_PREFIX", "Environment", "LogLevel", "Settings", "get_settings"]

ENV_PREFIX = "MOTOSPHERE_"


class Environment(StrEnum):
    """Where the application is running."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """How much detail the application writes to its log."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """All backend settings, validated once at load time and read-only afterwards."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
    )

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Where MotoSphere is running: development, test or production.",
    )
    api_host: str = Field(
        default="127.0.0.1",
        min_length=1,
        description=(
            "The network address the API listens on. The default only accepts "
            "connections from this computer."
        ),
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="The port number the API listens on, from 1 to 65535.",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description=(
            "How much detail is written to the log: DEBUG, INFO, WARNING, ERROR or CRITICAL."
        ),
    )

    @field_validator("environment", mode="before")
    @classmethod
    def _normalise_environment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application settings, loaded once and then reused.

    Call ``get_settings.cache_clear()`` to force the next call to reload them.
    """
    return Settings()
