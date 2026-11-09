"""Optional OpenTelemetry spans. Does nothing unless ``opentelemetry-api`` is installed."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

try:
    from opentelemetry import trace

    _tracer: Any = trace.get_tracer("streamforge")
except ImportError:  # the otel extra is optional
    _tracer = None


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[None]:
    """Open a span named ``name`` with the given attributes, or do nothing without OTel."""
    if _tracer is None:
        yield
        return
    with _tracer.start_as_current_span(name) as current:
        for key, value in attributes.items():
            current.set_attribute(key, value)
        yield
