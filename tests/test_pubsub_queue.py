from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("google.api_core")

from google.api_core import exceptions  # noqa: E402

from streamforge.adapters.pubsub_queue import PubSubQueue  # noqa: E402
from streamforge.domain import QueueError  # noqa: E402


class FakeFuture:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def result(self, timeout: float | None = None) -> str:
        if self._error:
            raise self._error
        return "message-id"


class FakePublisher:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.published: list[tuple[str, bytes]] = []

    def topic_path(self, project: str, topic: str) -> str:
        return f"projects/{project}/topics/{topic}"

    def publish(self, path: str, data: bytes) -> FakeFuture:
        self.published.append((path, data))
        return FakeFuture(self.error)


class FakeSubscriber:
    def __init__(self) -> None:
        self.received: list[Any] = []
        self.pull_error: Exception | None = None
        self.call_error: Exception | None = None
        self.acked: list[dict[str, Any]] = []
        self.modified: list[dict[str, Any]] = []

    def subscription_path(self, project: str, subscription: str) -> str:
        return f"projects/{project}/subscriptions/{subscription}"

    def pull(self, request: dict[str, Any], timeout: float) -> SimpleNamespace:
        if self.pull_error:
            raise self.pull_error
        return SimpleNamespace(received_messages=self.received)

    def acknowledge(self, request: dict[str, Any]) -> None:
        if self.call_error:
            raise self.call_error
        self.acked.append(request)

    def modify_ack_deadline(self, request: dict[str, Any]) -> None:
        if self.call_error:
            raise self.call_error
        self.modified.append(request)


def received(data: bytes, ack_id: str = "a1", attempt: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        ack_id=ack_id, message=SimpleNamespace(data=data), delivery_attempt=attempt
    )


def make_queue(
    publisher: FakePublisher | None = None, subscriber: FakeSubscriber | None = None
) -> tuple[PubSubQueue, FakePublisher, FakeSubscriber]:
    publisher = publisher or FakePublisher()
    subscriber = subscriber or FakeSubscriber()
    return PubSubQueue("proj", "events", "worker", publisher, subscriber), publisher, subscriber


def test_publish_sends_bytes_to_the_topic_path() -> None:
    queue, publisher, _ = make_queue()
    queue.publish(b"hello")
    assert publisher.published == [("projects/proj/topics/events", b"hello")]


def test_pull_wraps_messages_and_defaults_the_delivery_attempt() -> None:
    queue, _, subscriber = make_queue()
    subscriber.received = [received(b"one"), received(b"two", "a2", attempt=3)]

    first, second = queue.pull(10)

    assert (first.data, first.delivery_attempt) == (b"one", 1)  # 0 means "not reported"
    assert (second.data, second.delivery_attempt) == (b"two", 3)


def test_ack_acknowledges_by_ack_id() -> None:
    queue, _, subscriber = make_queue()
    subscriber.received = [received(b"x", "ack-7")]
    [message] = queue.pull(1)

    message.ack()

    assert subscriber.acked == [
        {"subscription": "projects/proj/subscriptions/worker", "ack_ids": ["ack-7"]}
    ]


def test_nack_sets_a_zero_ack_deadline() -> None:
    queue, _, subscriber = make_queue()
    subscriber.received = [received(b"x", "ack-7")]
    [message] = queue.pull(1)

    message.nack()

    [request] = subscriber.modified
    assert request["ack_ids"] == ["ack-7"]
    assert request["ack_deadline_seconds"] == 0


def test_an_empty_pull_timeout_returns_no_messages() -> None:
    queue, _, subscriber = make_queue()
    subscriber.pull_error = exceptions.DeadlineExceeded("no messages")
    assert queue.pull(10) == []


def test_pull_failure_is_a_queue_error_without_details() -> None:
    queue, _, subscriber = make_queue()
    subscriber.pull_error = exceptions.ServiceUnavailable("secret internal detail")

    with pytest.raises(QueueError) as info:
        queue.pull(10)

    assert "ServiceUnavailable" in str(info.value)
    assert "secret internal detail" not in str(info.value)


@pytest.mark.parametrize("error", [exceptions.Forbidden("no"), TimeoutError()])
def test_publish_failure_and_timeout_are_queue_errors(error: Exception) -> None:
    queue, _, _ = make_queue(publisher=FakePublisher(error))
    with pytest.raises(QueueError, match="publish failed"):
        queue.publish(b"x")


def test_ack_failure_is_a_queue_error() -> None:
    queue, _, subscriber = make_queue()
    subscriber.received = [received(b"x")]
    [message] = queue.pull(1)
    subscriber.call_error = exceptions.DeadlineExceeded("slow")

    with pytest.raises(QueueError, match="acknowledge failed"):
        message.ack()
