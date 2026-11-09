"""Runtime configuration, read from environment variables prefixed with ``SF_``."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings. Secrets use ``SecretStr`` so they never appear in logs or reprs."""

    model_config = SettingsConfigDict(env_prefix="SF_", env_file=".env", extra="ignore")

    queue_backend: Literal["local", "pubsub"] = "local"
    store_backend: Literal["memory", "postgres"] = "memory"

    database_url: SecretStr | None = None
    pubsub_project: str | None = None
    pubsub_topic: str | None = None
    pubsub_subscription: str | None = None

    schema_dir: Path = Path("schemas")
    rules_path: Path = Path("quality/rules.yaml")
    migrations_dir: Path = Path("migrations")

    max_delivery_attempts: int = Field(default=5, ge=1)
    batch_size: int = Field(default=100, ge=1, le=1000)
    poll_interval_seconds: float = Field(default=1.0, gt=0)

    metrics_port: int = Field(default=9100, ge=1, le=65535)
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _check_backends(self) -> Settings:
        if self.store_backend == "postgres" and self.database_url is None:
            raise ValueError("SF_DATABASE_URL is required when SF_STORE_BACKEND=postgres")
        if self.queue_backend == "pubsub" and not all(
            (self.pubsub_project, self.pubsub_topic, self.pubsub_subscription)
        ):
            raise ValueError(
                "SF_PUBSUB_PROJECT, SF_PUBSUB_TOPIC and SF_PUBSUB_SUBSCRIPTION "
                "are required when SF_QUEUE_BACKEND=pubsub"
            )
        return self
