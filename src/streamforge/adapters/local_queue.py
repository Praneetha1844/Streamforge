"""In-process queue for tests and local development."""

from __future__ import annotations

import threading
from collections import deque

from streamforge.ports import Message


class LocalQueue:
    """Thread-safe FIFO queue with at-least-once semantics.

    A ``nack`` re-enqueues the message at the tail with ``delivery_attempt`` incremented.
    shortcut: not shared across processes and not durable, use PubSubQueue for real deployments.
    """

    def __init__(self) -> None:
        self._items: deque[tuple[bytes, int]] = deque()
        self._lock = threading.Lock()

    def publish(self, data: bytes) -> None:
        with self._lock:
            self._items.append((data, 1))

    def pull(self, max_messages: int) -> list[Message]:
        messages: list[Message] = []
        with self._lock:
            while self._items and len(messages) < max_messages:
                data, attempt = self._items.popleft()
                messages.append(self._message(data, attempt))
        return messages

    def _message(self, data: bytes, attempt: int) -> Message:
        def nack() -> None:
            with self._lock:
                self._items.append((data, attempt + 1))

        return Message(data=data, ack=lambda: None, nack=nack, delivery_attempt=attempt)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
