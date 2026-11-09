"""Prometheus metrics. Each ``Metrics`` owns its registry so tests stay isolated."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram


class Metrics:
    """Counters and a latency histogram for the processing pipeline and the API."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()
        self.processed = Counter(
            "streamforge_events_processed",
            "Events validated, transformed and stored for the first time.",
            registry=self.registry,
        )
        self.duplicates = Counter(
            "streamforge_events_duplicates",
            "Events skipped because an event with the same id was already stored.",
            registry=self.registry,
        )
        self.dead_lettered = Counter(
            "streamforge_events_dead_lettered",
            "Messages routed to the dead-letter store.",
            ["reason"],
            registry=self.registry,
        )
        self.retries = Counter(
            "streamforge_events_retried",
            "Messages negatively acknowledged for redelivery after a store failure.",
            registry=self.registry,
        )
        self.latency = Histogram(
            "streamforge_processing_seconds",
            "Time to handle one message, from pull to acknowledgement.",
            registry=self.registry,
        )
        self.api_requests = Counter(
            "streamforge_api_requests",
            "Read API requests by route.",
            ["route"],
            registry=self.registry,
        )
