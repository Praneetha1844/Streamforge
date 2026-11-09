from typing import Any

import pytest
from conftest import FIXED_NOW, Harness, HarnessFactory, make_event

from streamforge.adapters.memory_store import InMemoryDeadLetters, InMemoryStore
from streamforge.domain import DeadLetter, Record, RejectReason, StoreError
from streamforge.pipeline import replay


class FlakyStore(InMemoryStore):
    """Fails the first ``failures`` upserts with a transient error."""

    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures

    def upsert(self, record: Record) -> bool:
        if self.failures > 0:
            self.failures -= 1
            raise StoreError("simulated outage")
        return super().upsert(record)


class BrokenDeadLetters(InMemoryDeadLetters):
    def put(self, dead_letter: DeadLetter) -> None:
        raise StoreError("simulated outage")


def only_dead_letter(h: Harness) -> DeadLetter:
    items = h.dead_letters.list_items(10)
    assert len(items) == 1
    return items[0]


def test_valid_event_is_transformed_and_stored(harness: Harness) -> None:
    harness.publish(make_event())

    result = harness.processor.process_batch(10)

    assert (result.processed, result.dead_lettered) == (1, 0)
    [record] = harness.store.list_events(None, 10)
    assert record.payload["currency"] == "USD"
    assert record.payload["total_cents"] == 1250
    assert record.processed_at == FIXED_NOW
    assert len(harness.queue) == 0
    assert harness.counter("streamforge_events_processed_total") == 1.0


def test_redelivered_event_is_stored_once(harness: Harness) -> None:
    harness.publish(make_event())
    harness.publish(make_event())

    result = harness.processor.process_batch(10)

    assert (result.processed, result.duplicates) == (1, 1)
    assert len(harness.store.list_events(None, 10)) == 1
    assert harness.counter("streamforge_events_duplicates_total") == 1.0


def test_non_json_is_dead_lettered(harness: Harness) -> None:
    harness.queue.publish(b"\xff not json")

    harness.processor.process_batch(10)

    dead = only_dead_letter(harness)
    assert dead.reason is RejectReason.INVALID_ENVELOPE
    assert dead.raw == b"\xff not json"


def test_invalid_envelope_detail_does_not_leak_payload_values(harness: Harness) -> None:
    event = make_event()
    del event["id"]
    event["payload"]["customer_id"] = "super-secret-value"
    harness.publish(event)

    harness.processor.process_batch(10)

    dead = only_dead_letter(harness)
    assert dead.reason is RejectReason.INVALID_ENVELOPE
    assert "id" in dead.detail
    assert "super-secret-value" not in dead.detail


def test_unknown_schema_is_dead_lettered(harness: Harness) -> None:
    harness.publish(make_event(type="order.unknown"))

    harness.processor.process_batch(10)

    assert only_dead_letter(harness).reason is RejectReason.UNKNOWN_SCHEMA


def test_schema_violation_is_dead_lettered(harness: Harness) -> None:
    event = make_event()
    event["payload"]["items"] = []
    harness.publish(event)

    harness.processor.process_batch(10)

    assert only_dead_letter(harness).reason is RejectReason.SCHEMA_VIOLATION
    assert harness.counter("streamforge_events_dead_lettered_total") == 0.0
    labelled = harness.metrics.registry.get_sample_value(
        "streamforge_events_dead_lettered_total", {"reason": "SCHEMA_VIOLATION"}
    )
    assert labelled == 1.0


def test_transform_failure_is_dead_lettered(build_harness: HarnessFactory) -> None:
    def boom(payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("bad transform")

    h = build_harness(transforms={"order.placed": boom})
    h.publish(make_event())

    h.processor.process_batch(10)

    dead = only_dead_letter(h)
    assert dead.reason is RejectReason.TRANSFORM_ERROR
    assert "bad transform" in dead.detail


def test_store_outage_is_retried_then_succeeds(build_harness: HarnessFactory) -> None:
    h = build_harness(store=FlakyStore(failures=1))
    h.publish(make_event())

    first = h.processor.process_batch(10)
    second = h.processor.process_batch(10)

    assert (first.retried, first.processed) == (1, 0)
    assert (second.retried, second.processed) == (0, 1)
    assert h.dead_letters.list_items(10) == []
    assert h.counter("streamforge_events_retried_total") == 1.0


def test_persistent_store_outage_ends_in_dead_letters(build_harness: HarnessFactory) -> None:
    h = build_harness(store=FlakyStore(failures=100), max_attempts=3)
    h.publish(make_event())

    results = [h.processor.process_batch(10) for _ in range(3)]

    assert [r.retried for r in results] == [1, 1, 0]
    assert results[2].dead_lettered == 1
    assert only_dead_letter(h).reason is RejectReason.SINK_FAILURE
    assert len(h.queue) == 0


def test_message_is_not_lost_when_dead_letter_write_fails(build_harness: HarnessFactory) -> None:
    h = build_harness(dead_letters=BrokenDeadLetters())
    h.queue.publish(b"not json")

    result = h.processor.process_batch(10)

    assert result.retried == 1
    assert len(h.queue) == 1  # redelivered, not acknowledged


def test_latency_is_observed_for_every_message(harness: Harness) -> None:
    harness.publish(make_event(id="a"))
    harness.queue.publish(b"garbage")

    harness.processor.process_batch(10)

    assert harness.counter("streamforge_processing_seconds_count") == 2.0


def test_batch_size_limits_messages_pulled(harness: Harness) -> None:
    for i in range(5):
        harness.publish(make_event(id=f"e{i}"))

    result = harness.processor.process_batch(2)

    assert result.total == 2
    assert len(harness.queue) == 3


def test_replay_moves_dead_letters_back_to_the_queue(harness: Harness) -> None:
    harness.publish(make_event(type="order.unknown"))
    harness.queue.publish(b"garbage")
    harness.processor.process_batch(10)

    replayed = replay(harness.dead_letters, harness.queue, [RejectReason.UNKNOWN_SCHEMA])

    assert replayed == 1
    assert len(harness.queue) == 1
    remaining = harness.dead_letters.list_items(10)
    assert [d.reason for d in remaining] == [RejectReason.INVALID_ENVELOPE]


def test_replay_without_filter_replays_everything_up_to_limit(harness: Harness) -> None:
    for i in range(3):
        harness.queue.publish(f"bad-{i}".encode())
    harness.processor.process_batch(10)

    assert replay(harness.dead_letters, harness.queue, limit=2) == 2
    assert len(harness.dead_letters.list_items(10)) == 1


@pytest.mark.parametrize("version", [1, 2])
def test_both_order_versions_are_processed(harness: Harness, version: int) -> None:
    harness.publish(make_event(schema_version=version))

    assert harness.processor.process_batch(10).processed == 1
