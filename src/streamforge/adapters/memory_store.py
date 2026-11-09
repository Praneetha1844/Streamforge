"""In-memory event store and dead-letter store for tests and local development."""

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import replace
from typing import Any

from streamforge.domain import DeadLetter, Record, RejectReason

ORDER_TYPE = "order.placed"


def compute_aggregates(records: Iterable[Record]) -> dict[str, Any]:
    """Event counts per type and order totals per currency."""
    by_type: Counter[str] = Counter()
    revenue: Counter[str] = Counter()
    for record in records:
        by_type[record.type] += 1
        if record.type == ORDER_TYPE:
            revenue[record.payload["currency"]] += record.payload["total_cents"]
    return {
        "events_by_type": dict(sorted(by_type.items())),
        "order_total_cents_by_currency": dict(sorted(revenue.items())),
    }


class InMemoryStore:
    """Event store keyed by event id. Upserts are idempotent."""

    def __init__(self) -> None:
        self._records: dict[str, Record] = {}
        self._lock = threading.Lock()

    def upsert(self, record: Record) -> bool:
        with self._lock:
            if record.event_id in self._records:
                return False
            self._records[record.event_id] = record
            return True

    def list_events(self, event_type: str | None, limit: int) -> list[Record]:
        with self._lock:
            records = [r for r in self._records.values() if event_type in (None, r.type)]
        records.sort(key=lambda r: (r.occurred_at, r.event_id), reverse=True)
        return records[:limit]

    def aggregates(self) -> dict[str, Any]:
        with self._lock:
            return compute_aggregates(self._records.values())

    def healthy(self) -> bool:
        return True


class InMemoryDeadLetters:
    """Dead-letter store that assigns incrementing ids."""

    def __init__(self) -> None:
        self._items: dict[int, DeadLetter] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def put(self, dead_letter: DeadLetter) -> None:
        with self._lock:
            self._items[self._next_id] = replace(dead_letter, id=self._next_id)
            self._next_id += 1

    def list_items(self, limit: int, reason: RejectReason | None = None) -> list[DeadLetter]:
        with self._lock:
            items = [d for d in self._items.values() if reason in (None, d.reason)]
        return items[:limit]

    def remove(self, ids: Sequence[int]) -> None:
        with self._lock:
            for item_id in ids:
                self._items.pop(item_id, None)
