"""Google Cloud Pub/Sub implementation of the queue port (requires the ``pubsub`` extra).

Messages are pulled synchronously. ``delivery_attempt`` is populated by Pub/Sub only when
the subscription has a dead-letter policy, which the Terraform in ``infra/terraform`` sets.

Every Pub/Sub failure is raised as ``QueueError`` carrying only the exception class name.
If an acknowledgement fails after a message was handled, Pub/Sub redelivers it, which the
idempotent store absorbs. The rest of a pulled batch is redelivered once its ack deadline
passes.
"""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions

from streamforge.domain import QueueError
from streamforge.ports import Message

_TIMEOUT_SECONDS = 30
# Publishing waits on a future, which raises the builtin TimeoutError when the wait runs out.
_PUBSUB_ERRORS = (exceptions.GoogleAPICallError, TimeoutError)


class PubSubQueue:
    """Publish to a topic and pull from a subscription."""

    def __init__(
        self,
        project: str,
        topic: str,
        subscription: str,
        publisher: Any = None,
        subscriber: Any = None,
    ) -> None:
        if publisher is None or subscriber is None:
            from google.cloud import pubsub_v1  # only needed when the clients are not injected

            publisher = publisher or pubsub_v1.PublisherClient()
            subscriber = subscriber or pubsub_v1.SubscriberClient()
        self._publisher = publisher
        self._subscriber = subscriber
        self._topic_path: str = publisher.topic_path(project, topic)
        self._subscription_path: str = subscriber.subscription_path(project, subscription)

    def publish(self, data: bytes) -> None:
        try:
            self._publisher.publish(self._topic_path, data).result(timeout=_TIMEOUT_SECONDS)
        except _PUBSUB_ERRORS as exc:
            raise QueueError(f"publish failed: {type(exc).__name__}") from exc

    def pull(self, max_messages: int) -> list[Message]:
        try:
            response = self._subscriber.pull(
                request={"subscription": self._subscription_path, "max_messages": max_messages},
                timeout=_TIMEOUT_SECONDS,
            )
        except exceptions.DeadlineExceeded:
            return []  # nothing available within the timeout
        except _PUBSUB_ERRORS as exc:
            raise QueueError(f"pull failed: {type(exc).__name__}") from exc
        return [self._wrap(received) for received in response.received_messages]

    def _wrap(self, received: Any) -> Message:
        ack_ids = [received.ack_id]

        def ack() -> None:
            self._call("acknowledge", {"ack_ids": ack_ids})

        def nack() -> None:
            # A zero ack deadline makes Pub/Sub redeliver the message immediately.
            self._call("modify_ack_deadline", {"ack_ids": ack_ids, "ack_deadline_seconds": 0})

        return Message(
            data=bytes(received.message.data),
            ack=ack,
            nack=nack,
            delivery_attempt=received.delivery_attempt or 1,
        )

    def _call(self, method: str, request: dict[str, Any]) -> None:
        try:
            getattr(self._subscriber, method)(
                request={"subscription": self._subscription_path, **request}
            )
        except _PUBSUB_ERRORS as exc:
            raise QueueError(f"{method} failed: {type(exc).__name__}") from exc
