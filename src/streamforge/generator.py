"""Seeded synthetic event generator for demos, tests and local runs."""

from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

_CURRENCIES = ("usd", "eur", "inr")
_CHANNELS = ("web", "mobile", "store")
_DEFAULT_START = datetime(2026, 1, 1, tzinfo=UTC)


def generate_events(
    count: int,
    seed: int,
    start: datetime = _DEFAULT_START,
    invalid_ratio: float = 0.0,
) -> Iterator[dict[str, Any]]:
    """Yield ``count`` events. The same arguments always produce the same events.

    About ``invalid_ratio`` of the events are deliberately corrupted (missing field,
    unknown type or out-of-range value) to exercise validation and dead-lettering.
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    if not 0.0 <= invalid_ratio <= 1.0:
        raise ValueError("invalid_ratio must be between 0 and 1")
    rng = random.Random(seed)
    for index in range(count):
        occurred = start + timedelta(seconds=index * 7 + rng.randint(0, 5))
        if rng.random() < 0.7:
            event = _order(rng, seed, index, occurred)
        else:
            event = _payment(rng, seed, index, occurred)
        if rng.random() < invalid_ratio:
            event = _corrupt(rng, event)
        yield event


def _envelope(
    event_type: str,
    version: int,
    seed: int,
    index: int,
    occurred: datetime,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"evt-{seed}-{index:08d}",
        "type": event_type,
        "source": "synthetic-generator",
        "schema_version": version,
        "occurred_at": occurred.isoformat(),
        "payload": payload,
    }


def _order(rng: random.Random, seed: int, index: int, occurred: datetime) -> dict[str, Any]:
    version = rng.choice((1, 2))
    payload: dict[str, Any] = {
        "order_id": f"ord-{seed}-{index:08d}",
        "customer_id": f"cus-{rng.randint(1, 500):04d}",
        "currency": rng.choice(_CURRENCIES),  # lower case on purpose: the pipeline normalises it
        "items": [
            {
                "sku": f"SKU-{rng.randint(1, 50):03d}",
                "qty": rng.randint(1, 5),
                "unit_price_cents": rng.randint(199, 9999),
            }
            for _ in range(rng.randint(1, 4))
        ],
    }
    if version == 2:
        payload["channel"] = rng.choice(_CHANNELS)
    return _envelope("order.placed", version, seed, index, occurred, payload)


def _payment(rng: random.Random, seed: int, index: int, occurred: datetime) -> dict[str, Any]:
    payload = {
        "payment_id": f"pay-{seed}-{index:08d}",
        "order_id": f"ord-{seed}-{max(index - 1, 0):08d}",
        "amount_cents": rng.randint(199, 40000),
        "currency": rng.choice(_CURRENCIES),
    }
    return _envelope("payment.settled", 1, seed, index, occurred, payload)


def _corrupt(rng: random.Random, event: dict[str, Any]) -> dict[str, Any]:
    broken = {**event, "payload": dict(event["payload"])}
    kind = rng.choice(("missing_field", "unknown_type", "bad_value"))
    if kind == "unknown_type":
        broken["type"] = "order.unknown"
    elif kind == "missing_field":
        broken["payload"].pop(next(iter(broken["payload"])))
    elif "items" in broken["payload"]:
        broken["payload"]["items"][0]["qty"] = -1
    else:
        broken["payload"]["amount_cents"] = -1
    return broken
