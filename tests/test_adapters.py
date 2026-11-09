from datetime import timedelta

from conftest import FIXED_NOW

from streamforge.adapters.local_queue import LocalQueue
from streamforge.adapters.memory_store import InMemoryDeadLetters, InMemoryStore
from streamforge.domain import DeadLetter, Record, RejectReason


def order(event_id: str, total: int, currency: str = "USD", age_minutes: int = 0) -> Record:
    return Record(
        event_id=event_id,
        type="order.placed",
        source="t",
        schema_version=1,
        occurred_at=FIXED_NOW - timedelta(minutes=age_minutes),
        processed_at=FIXED_NOW,
        payload={"currency": currency, "total_cents": total},
    )


def test_local_queue_is_fifo_and_respects_max_messages() -> None:
    queue = LocalQueue()
    for i in range(3):
        queue.publish(str(i).encode())

    first = queue.pull(2)

    assert [m.data for m in first] == [b"0", b"1"]
    assert len(queue) == 1


def test_nack_requeues_with_incremented_attempt() -> None:
    queue = LocalQueue()
    queue.publish(b"x")
    [message] = queue.pull(1)
    assert message.delivery_attempt == 1

    message.nack()

    [again] = queue.pull(1)
    assert (again.data, again.delivery_attempt) == (b"x", 2)


def test_ack_does_not_requeue() -> None:
    queue = LocalQueue()
    queue.publish(b"x")
    [message] = queue.pull(1)
    message.ack()
    assert queue.pull(1) == []


def test_store_upsert_is_idempotent() -> None:
    store = InMemoryStore()
    assert store.upsert(order("a", 100)) is True
    assert store.upsert(order("a", 999)) is False
    [record] = store.list_events(None, 10)
    assert record.payload["total_cents"] == 100


def test_store_lists_newest_first_with_filter_and_limit() -> None:
    store = InMemoryStore()
    store.upsert(order("old", 1, age_minutes=30))
    store.upsert(order("new", 2, age_minutes=1))
    store.upsert(
        Record("pay", "payment.settled", "t", 1, FIXED_NOW, FIXED_NOW, {"amount_cents": 5})
    )

    assert [r.event_id for r in store.list_events("order.placed", 10)] == ["new", "old"]
    assert [r.event_id for r in store.list_events(None, 1)] == ["pay"]


def test_store_aggregates() -> None:
    store = InMemoryStore()
    store.upsert(order("a", 100, "USD"))
    store.upsert(order("b", 250, "USD"))
    store.upsert(order("c", 40, "EUR"))

    assert store.aggregates() == {
        "events_by_type": {"order.placed": 3},
        "order_total_cents_by_currency": {"EUR": 40, "USD": 350},
    }


def test_dead_letters_assign_ids_filter_and_remove() -> None:
    dead = InMemoryDeadLetters()
    dead.put(DeadLetter(b"a", RejectReason.SCHEMA_VIOLATION, "d", FIXED_NOW))
    dead.put(DeadLetter(b"b", RejectReason.UNKNOWN_SCHEMA, "d", FIXED_NOW))

    items = dead.list_items(10)
    assert [d.id for d in items] == [1, 2]
    assert [d.raw for d in dead.list_items(10, RejectReason.UNKNOWN_SCHEMA)] == [b"b"]

    dead.remove([1, 99])
    assert [d.id for d in dead.list_items(10)] == [2]
