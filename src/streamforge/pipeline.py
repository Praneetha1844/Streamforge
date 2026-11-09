"""The processing pipeline: pull, validate, transform, store, acknowledge.

Delivery is at-least-once. Redeliveries are safe because the store upsert is idempotent.
Messages that can never succeed are written to the dead-letter store with a reason code
and then acknowledged, so they cannot block the queue.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from streamforge.domain import (
    DeadLetter,
    Event,
    Record,
    RejectReason,
    SchemaViolation,
    StoreError,
    UnknownSchema,
)
from streamforge.metrics import Metrics
from streamforge.ports import DeadLetterStore, EventStore, Message, Queue
from streamforge.registry import SchemaRegistry
from streamforge.tracing import span
from streamforge.transform import Transform, identity

log = logging.getLogger(__name__)

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Current time in UTC."""
    return datetime.now(UTC)


class _Rejected(Exception):
    """Internal signal: the message must be dead-lettered."""

    def __init__(self, reason: RejectReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(slots=True)
class BatchResult:
    """Outcome counts for one ``process_batch`` call."""

    processed: int = 0
    duplicates: int = 0
    dead_lettered: int = 0
    retried: int = 0

    @property
    def total(self) -> int:
        """Messages handled in the batch."""
        return self.processed + self.duplicates + self.dead_lettered + self.retried


class Processor:
    """Handles messages from a queue and writes results to a store."""

    def __init__(
        self,
        queue: Queue,
        store: EventStore,
        dead_letters: DeadLetterStore,
        registry: SchemaRegistry,
        transforms: Mapping[str, Transform],
        metrics: Metrics,
        max_attempts: int = 5,
        clock: Clock = utc_now,
    ) -> None:
        self._queue = queue
        self._store = store
        self._dead_letters = dead_letters
        self._registry = registry
        self._transforms = transforms
        self._metrics = metrics
        self._max_attempts = max_attempts
        self._clock = clock

    def process_batch(self, max_messages: int) -> BatchResult:
        """Pull up to ``max_messages`` and handle each one."""
        result = BatchResult()
        for message in self._queue.pull(max_messages):
            self._handle(message, result)
        return result

    def _handle(self, message: Message, result: BatchResult) -> None:
        started = time.perf_counter()
        try:
            with span("streamforge.handle", delivery_attempt=message.delivery_attempt):
                self._process(message, result)
        finally:
            self._metrics.latency.observe(time.perf_counter() - started)

    def _process(self, message: Message, result: BatchResult) -> None:
        try:
            record = self._build_record(message.data)
        except _Rejected as rejected:
            self._dead_letter(message, rejected.reason, rejected.detail, result)
            return
        try:
            inserted = self._store.upsert(record)
        except StoreError as exc:
            self._on_store_failure(message, exc, result)
            return
        message.ack()
        if inserted:
            result.processed += 1
            self._metrics.processed.inc()
        else:
            result.duplicates += 1
            self._metrics.duplicates.inc()

    def _build_record(self, data: bytes) -> Record:
        event = self._parse(data)
        try:
            self._registry.validate(event)
        except UnknownSchema as exc:
            raise _Rejected(RejectReason.UNKNOWN_SCHEMA, str(exc)) from exc
        except SchemaViolation as exc:
            raise _Rejected(RejectReason.SCHEMA_VIOLATION, str(exc)) from exc
        transform = self._transforms.get(event.type, identity)
        try:
            payload = transform(dict(event.payload))
        except Exception as exc:  # a transform bug must not block the queue
            raise _Rejected(RejectReason.TRANSFORM_ERROR, f"{type(exc).__name__}: {exc}") from exc
        return Record(
            event_id=event.id,
            type=event.type,
            source=event.source,
            schema_version=event.schema_version,
            occurred_at=event.occurred_at,
            processed_at=self._clock(),
            payload=payload,
        )

    @staticmethod
    def _parse(data: bytes) -> Event:
        try:
            raw: Any = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _Rejected(RejectReason.INVALID_ENVELOPE, f"not valid JSON: {exc}") from exc
        try:
            return Event.model_validate(raw)
        except ValidationError as exc:
            # include_input=False keeps payload values out of logs and dead-letter details
            problems = [
                f"{'/'.join(map(str, e['loc'])) or '<root>'}: {e['msg']}"
                for e in exc.errors(include_input=False)
            ]
            raise _Rejected(RejectReason.INVALID_ENVELOPE, "; ".join(problems)) from exc

    def _on_store_failure(self, message: Message, exc: StoreError, result: BatchResult) -> None:
        attempt = message.delivery_attempt
        if attempt >= self._max_attempts:
            detail = f"store failed after {attempt} attempts: {exc}"
            self._dead_letter(message, RejectReason.SINK_FAILURE, detail, result)
            return
        log.warning("store failure, message will be redelivered", extra={"attempt": attempt})
        message.nack()
        result.retried += 1
        self._metrics.retries.inc()

    def _dead_letter(
        self, message: Message, reason: RejectReason, detail: str, result: BatchResult
    ) -> None:
        dead_letter = DeadLetter(
            raw=message.data, reason=reason, detail=detail, failed_at=self._clock()
        )
        try:
            self._dead_letters.put(dead_letter)
        except StoreError:
            # Never ack a message we failed to preserve: redeliver it instead of losing it.
            log.exception("could not write dead letter, message will be redelivered")
            message.nack()
            result.retried += 1
            self._metrics.retries.inc()
            return
        message.ack()
        result.dead_lettered += 1
        self._metrics.dead_lettered.labels(reason=reason.value).inc()
        log.warning("message dead-lettered", extra={"reason": reason.value, "detail": detail})


def replay(
    dead_letters: DeadLetterStore,
    queue: Queue,
    reasons: Sequence[RejectReason] | None = None,
    limit: int = 1000,
) -> int:
    """Re-publish dead letters to the queue and remove them. Return how many were replayed.

    Each message is removed only after it has been published, so a failure mid-way
    cannot lose messages (it can duplicate them, which the idempotent store absorbs).
    """
    replayed = 0
    selected: list[RejectReason | None] = list(reasons) if reasons else [None]
    for reason in selected:
        for item in dead_letters.list_items(limit - replayed, reason):
            queue.publish(item.raw)
            if item.id is not None:
                dead_letters.remove([item.id])
            replayed += 1
        if replayed >= limit:
            break
    return replayed
