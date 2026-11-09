"""Interfaces (ports) the core depends on. Adapters implement them."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from streamforge.domain import DeadLetter, Record, RejectReason


@dataclass(slots=True)
class Message:
    """A pulled message with its acknowledgement callbacks.

    ``delivery_attempt`` starts at 1 and increases each time the message is redelivered.
    """

    data: bytes
    ack: Callable[[], None]
    nack: Callable[[], None]
    delivery_attempt: int = 1


class Queue(Protocol):
    """At-least-once message queue."""

    def publish(self, data: bytes) -> None: ...

    def pull(self, max_messages: int) -> list[Message]: ...


class EventStore(Protocol):
    """Idempotent storage and read access for processed events."""

    def upsert(self, record: Record) -> bool:
        """Store the record. Return ``False`` if an event with the same id already exists."""
        ...

    def list_events(self, event_type: str | None, limit: int) -> list[Record]: ...

    def aggregates(self) -> dict[str, Any]: ...

    def healthy(self) -> bool: ...


class DeadLetterStore(Protocol):
    """Storage for messages that could not be processed."""

    def put(self, dead_letter: DeadLetter) -> None: ...

    def list_items(self, limit: int, reason: RejectReason | None = None) -> list[DeadLetter]: ...

    def remove(self, ids: Sequence[int]) -> None: ...
