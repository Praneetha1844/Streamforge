"""Composition root: builds the object graph for the chosen backends."""

from __future__ import annotations

from dataclasses import dataclass

from streamforge.adapters.local_queue import LocalQueue
from streamforge.adapters.memory_store import InMemoryDeadLetters, InMemoryStore
from streamforge.config import Settings
from streamforge.metrics import Metrics
from streamforge.pipeline import Processor
from streamforge.ports import DeadLetterStore, EventStore, Queue
from streamforge.registry import SchemaRegistry
from streamforge.transform import default_transforms


@dataclass(slots=True)
class App:
    """Everything the CLI needs to run, wired together."""

    settings: Settings
    queue: Queue
    store: EventStore
    dead_letters: DeadLetterStore
    metrics: Metrics
    processor: Processor


def build_stores(settings: Settings) -> tuple[EventStore, DeadLetterStore]:
    """Create the event store and dead-letter store for the configured backend."""
    if settings.store_backend == "postgres":
        from streamforge.adapters.postgres_store import PostgresStore

        if settings.database_url is None:
            raise ValueError("SF_DATABASE_URL is required for the postgres store")
        postgres = PostgresStore(settings.database_url.get_secret_value())
        return postgres, postgres
    return InMemoryStore(), InMemoryDeadLetters()


def build_queue(settings: Settings) -> Queue:
    """Create the queue for the configured backend."""
    if settings.queue_backend == "pubsub":
        from streamforge.adapters.pubsub_queue import PubSubQueue

        assert settings.pubsub_project and settings.pubsub_topic and settings.pubsub_subscription
        return PubSubQueue(
            settings.pubsub_project, settings.pubsub_topic, settings.pubsub_subscription
        )
    return LocalQueue()


def build_app(settings: Settings, metrics: Metrics | None = None) -> App:
    """Wire the processor to its queue, stores, schema registry and metrics."""
    metrics = metrics or Metrics()
    queue = build_queue(settings)
    store, dead_letters = build_stores(settings)
    processor = Processor(
        queue=queue,
        store=store,
        dead_letters=dead_letters,
        registry=SchemaRegistry.from_dir(settings.schema_dir),
        transforms=default_transforms(),
        metrics=metrics,
        max_attempts=settings.max_delivery_attempts,
    )
    return App(settings, queue, store, dead_letters, metrics, processor)
