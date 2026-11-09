from datetime import UTC, datetime
from typing import Any

import pytest
from conftest import FIXED_NOW

psycopg = pytest.importorskip("psycopg")

from streamforge.adapters.postgres_store import PostgresStore  # noqa: E402
from streamforge.domain import DeadLetter, Record, RejectReason, StoreError  # noqa: E402


@pytest.fixture
def unreachable_store(monkeypatch: pytest.MonkeyPatch) -> PostgresStore:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise psycopg.OperationalError("password=hunter2 host=10.0.0.5")

    monkeypatch.setattr(psycopg, "connect", refuse)
    return PostgresStore("postgresql://unused")


def record() -> Record:
    return Record("e1", "order.placed", "t", 1, FIXED_NOW, FIXED_NOW, {"a": 1})


def test_connection_errors_expose_only_the_exception_class(
    unreachable_store: PostgresStore,
) -> None:
    with pytest.raises(StoreError) as info:
        unreachable_store.upsert(record())

    assert "OperationalError" in str(info.value)
    assert "hunter2" not in str(info.value)
    assert "10.0.0.5" not in str(info.value)


def test_every_operation_reports_store_errors(unreachable_store: PostgresStore) -> None:
    dead = DeadLetter(b"x", RejectReason.INVALID_ENVELOPE, "d", datetime(2026, 1, 1, tzinfo=UTC))
    for call in (
        lambda: unreachable_store.list_events(None, 10),
        lambda: unreachable_store.aggregates(),
        lambda: unreachable_store.put(dead),
        lambda: unreachable_store.list_items(10),
        lambda: unreachable_store.remove([1]),
    ):
        with pytest.raises(StoreError):
            call()


def test_health_is_false_when_the_database_is_unreachable(
    unreachable_store: PostgresStore,
) -> None:
    assert unreachable_store.healthy() is False


def test_removing_nothing_does_not_connect(unreachable_store: PostgresStore) -> None:
    unreachable_store.remove([])  # would raise StoreError if it tried to connect
