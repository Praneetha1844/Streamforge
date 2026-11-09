"""PostgreSQL implementation of the event store and the dead-letter store.

shortcut: one short-lived connection per call keeps the code simple and stateless,
switch to ``psycopg_pool.ConnectionPool`` if connection set-up cost becomes visible.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from streamforge.domain import DeadLetter, Record, RejectReason, StoreError


class PostgresStore:
    """Stores events idempotently (``ON CONFLICT DO NOTHING``) and dead letters."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        try:
            with psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=5) as conn:
                yield conn
        except psycopg.Error as exc:
            # Only the exception class is exposed: messages can contain connection details.
            raise StoreError(f"database error: {type(exc).__name__}") from exc

    # --- EventStore -----------------------------------------------------------------

    def upsert(self, record: Record) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT INTO events (event_id, type, source, schema_version, occurred_at,"
                " processed_at, payload) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (event_id) DO NOTHING",
                (
                    record.event_id,
                    record.type,
                    record.source,
                    record.schema_version,
                    record.occurred_at,
                    record.processed_at,
                    Jsonb(record.payload),
                ),
            )
            return cursor.rowcount == 1

    def list_events(self, event_type: str | None, limit: int) -> list[Record]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT event_id, type, source, schema_version, occurred_at, processed_at, payload"
                " FROM events WHERE (%s::text IS NULL OR type = %s)"
                " ORDER BY occurred_at DESC, event_id DESC LIMIT %s",
                (event_type, event_type, limit),
            ).fetchall()
        return [Record(**row) for row in rows]

    def aggregates(self) -> dict[str, Any]:
        with self._connection() as conn:
            by_type = conn.execute(
                "SELECT type, count(*) AS n FROM events GROUP BY type ORDER BY type"
            ).fetchall()
            revenue = conn.execute(
                "SELECT payload->>'currency' AS currency,"
                " sum((payload->>'total_cents')::bigint) AS total"
                " FROM events WHERE type = 'order.placed' GROUP BY 1 ORDER BY 1"
            ).fetchall()
        return {
            "events_by_type": {row["type"]: row["n"] for row in by_type},
            "order_total_cents_by_currency": {
                row["currency"]: int(row["total"]) for row in revenue
            },
        }

    def healthy(self) -> bool:
        try:
            with self._connection() as conn:
                conn.execute("SELECT 1")
        except StoreError:
            return False
        return True

    # --- DeadLetterStore ------------------------------------------------------------

    def put(self, dead_letter: DeadLetter) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO dead_letters (raw, reason, detail, failed_at)"
                " VALUES (%s, %s, %s, %s)",
                (
                    dead_letter.raw,
                    dead_letter.reason.value,
                    dead_letter.detail,
                    dead_letter.failed_at,
                ),
            )

    def list_items(self, limit: int, reason: RejectReason | None = None) -> list[DeadLetter]:
        reason_value = reason.value if reason else None
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT id, raw, reason, detail, failed_at FROM dead_letters"
                " WHERE (%s::text IS NULL OR reason = %s) ORDER BY id LIMIT %s",
                (reason_value, reason_value, limit),
            ).fetchall()
        return [
            DeadLetter(
                id=row["id"],
                raw=bytes(row["raw"]),
                reason=RejectReason(row["reason"]),
                detail=row["detail"],
                failed_at=row["failed_at"],
            )
            for row in rows
        ]

    def remove(self, ids: Sequence[int]) -> None:
        if not ids:
            return
        with self._connection() as conn:
            conn.execute("DELETE FROM dead_letters WHERE id = ANY(%s)", (list(ids),))
