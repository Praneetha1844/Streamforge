"""Google Cloud Pub/Sub implementation of the queue port (requires the ``pubsub`` extra).

Messages are pulled synchronously. ``delivery_attempt`` is populated by Pub/Sub only when
the subscription has a dead-letter policy, which the Terraform in ``infra/terraform`` sets.
"""

from __future__ import annotations

from typing import Any

from streamforge.domain import QueueError
from streamforge.ports import Message

_TIMEOUT_SECONDS = 30


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
        from google.cloud import pubsub_v1  # imported here so the core works without the extra

        self._publisher = publisher or pubsub_v1.PublisherClient()
        self._subscriber = subscriber or pubsub_v1.SubscriberClient()
        self._topic_path: str = self._publisher.topic_path(project, topic)
        self._subscription_path: str = self._subscriber.subscription_path(project, subscription)

    def publish(self, data: bytes) -> None:
        from google.api_core import exceptions

        try:
            self._publisher.publish(self._topic_path, data).result(timeout=_TIMEOUT_SECONDS)
        except exceptions.GoogleAPICallError as exc:
            raise QueueError(f"publish failed: {type(exc).__name__}") from exc

    def pull(self, max_messages: int) -> list[Message]:
        from google.api_core import exceptions

        try:
            response = self._subscriber.pull(
                request={"subscription": self._subscription_path, "max_messages": max_messages},
                timeout=_TIMEOUT_SECONDS,
            )
        except exceptions.DeadlineExceeded:
            return []  # nothing available within the timeout
        except exceptions.GoogleAPICallError as exc:
            raise QueueError(f"pull failed: {type(exc).__name__}") from exc
        return [self._wrap(received) for received in response.received_messages]

    def _wrap(self, received: Any) -> Message:
        ack_ids = [received.ack_id]
        path = self._subscription_path

        def ack() -> None:
            self._subscriber.acknowledge(request={"subscription": path, "ack_ids": ack_ids})

        def nack() -> None:
            # A zero ack deadline makes Pub/Sub redeliver the message immediately.
            self._subscriber.modify_ack_deadline(
                request={"subscription": path, "ack_ids": ack_ids, "ack_deadline_seconds": 0}
            )

        return Message(
            data=bytes(received.message.data),
            ack=ack,
            nack=nack,
            delivery_attempt=received.delivery_attempt or 1,
        )
