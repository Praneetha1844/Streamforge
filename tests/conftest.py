"""Shared fixtures: a real schema registry and a fully in-memory pipeline harness."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from streamforge.adapters.local_queue import LocalQueue
from streamforge.adapters.memory_store import InMemoryDeadLetters, InMemoryStore
from streamforge.metrics import Metrics
from streamforge.pipeline import Processor
from streamforge.ports import DeadLetterStore, EventStore
from streamforge.registry import SchemaRegistry
from streamforge.transform import Transform, default_transforms

ROOT = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def make_event(**overrides: Any) -> dict[str, Any]:
    """A valid order.placed v1 event. Total is 1250 cents over 3 items."""
    event: dict[str, Any] = {
        "id": "evt-1",
        "type": "order.placed",
        "source": "test",
        "schema_version": 1,
        "occurred_at": "2026-01-01T00:00:00+00:00",
        "payload": {
            "order_id": "ord-1",
            "customer_id": "cus-1",
            "currency": "usd",
            "items": [
                {"sku": "A", "qty": 2, "unit_price_cents": 500},
                {"sku": "B", "qty": 1, "unit_price_cents": 250},
            ],
        },
    }
    event.update(overrides)
    return event


@dataclass
class Harness:
    """A processor wired to in-memory adapters, with helpers for tests."""

    queue: LocalQueue
    store: EventStore
    dead_letters: DeadLetterStore
    metrics: Metrics
    processor: Processor

    def publish(self, event: Mapping[str, Any]) -> None:
        self.queue.publish(json.dumps(event).encode("utf-8"))

    def counter(self, name: str) -> float:
        return self.metrics.registry.get_sample_value(name) or 0.0


HarnessFactory = Callable[..., Harness]


@pytest.fixture(scope="session")
def schema_dir() -> Path:
    return ROOT / "schemas"


@pytest.fixture
def registry(schema_dir: Path) -> SchemaRegistry:
    return SchemaRegistry.from_dir(schema_dir)


@pytest.fixture
def build_harness(registry: SchemaRegistry) -> HarnessFactory:
    def factory(
        store: EventStore | None = None,
        dead_letters: DeadLetterStore | None = None,
        transforms: Mapping[str, Transform] | None = None,
        max_attempts: int = 3,
    ) -> Harness:
        queue = LocalQueue()
        store = store or InMemoryStore()
        dead_letters = dead_letters or InMemoryDeadLetters()
        metrics = Metrics()
        processor = Processor(
            queue=queue,
            store=store,
            dead_letters=dead_letters,
            registry=registry,
            transforms=default_transforms() if transforms is None else transforms,
            metrics=metrics,
            max_attempts=max_attempts,
            clock=lambda: FIXED_NOW,
        )
        return Harness(queue, store, dead_letters, metrics, processor)

    return factory


@pytest.fixture
def harness(build_harness: HarnessFactory) -> Harness:
    return build_harness()
