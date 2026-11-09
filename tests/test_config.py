import pytest
from pydantic import ValidationError

from streamforge.config import Settings


def test_defaults_run_without_any_external_service() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (settings.queue_backend, settings.store_backend) == ("local", "memory")


def test_postgres_backend_requires_a_database_url() -> None:
    with pytest.raises(ValidationError, match="SF_DATABASE_URL"):
        Settings(_env_file=None, store_backend="postgres")  # type: ignore[call-arg]


def test_pubsub_backend_requires_project_topic_and_subscription() -> None:
    with pytest.raises(ValidationError, match="SF_PUBSUB_PROJECT"):
        Settings(_env_file=None, queue_backend="pubsub", pubsub_project="p")  # type: ignore[call-arg]


def test_database_url_is_not_exposed_in_repr() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        store_backend="postgres",
        database_url="postgresql://user:hunter2@host/db",  # type: ignore[arg-type]
    )
    assert "hunter2" not in repr(settings)
    assert settings.database_url is not None
    assert "hunter2" in settings.database_url.get_secret_value()


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SF_BATCH_SIZE", "7")
    assert Settings(_env_file=None).batch_size == 7  # type: ignore[call-arg]


def test_out_of_range_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, batch_size=0)  # type: ignore[call-arg]


def test_api_key_is_optional_and_hidden_in_repr() -> None:
    assert Settings(_env_file=None).api_key is None  # type: ignore[call-arg]
    settings = Settings(_env_file=None, api_key="s3cret")  # type: ignore[call-arg,arg-type]
    assert "s3cret" not in repr(settings)
