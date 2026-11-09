"""Pure payload transformations, composed per event type."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Payload = dict[str, Any]
Transform = Callable[[Payload], Payload]


def compose(*steps: Transform) -> Transform:
    """Chain transforms left to right into one transform."""

    def run(payload: Payload) -> Payload:
        for step in steps:
            payload = step(payload)
        return payload

    return run


def normalise_currency(payload: Payload) -> Payload:
    """Upper-case the ISO currency code."""
    return {**payload, "currency": payload["currency"].upper()}


def derive_order_totals(payload: Payload) -> Payload:
    """Add ``item_count`` and ``total_cents`` computed from the line items."""
    items = payload["items"]
    return {
        **payload,
        "item_count": sum(item["qty"] for item in items),
        "total_cents": sum(item["qty"] * item["unit_price_cents"] for item in items),
    }


def identity(payload: Payload) -> Payload:
    """Pass the payload through unchanged."""
    return payload


def default_transforms() -> dict[str, Transform]:
    """Transforms keyed by event type. Types not listed use ``identity``."""
    return {
        "order.placed": compose(normalise_currency, derive_order_totals),
        "payment.settled": normalise_currency,
    }
