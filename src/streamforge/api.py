"""Read-only HTTP API over the event store, plus the Prometheus scrape endpoint."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from streamforge import __version__
from streamforge.bootstrap import build_stores
from streamforge.config import Settings
from streamforge.domain import StoreError
from streamforge.logging_setup import configure_logging
from streamforge.metrics import Metrics
from streamforge.ports import EventStore


def create_app(
    store: EventStore, metrics: Metrics | None = None, api_key: str | None = None
) -> FastAPI:
    """Build the FastAPI application around an event store.

    With ``api_key`` set, the data routes require it in the ``X-API-Key`` header.
    ``/health`` and ``/metrics`` stay open for probes and scrapers.
    """
    metrics = metrics or Metrics()
    app = FastAPI(title="Streamforge", version=__version__)

    def require_key(x_api_key: str | None = Header(default=None)) -> None:
        if api_key is None:
            return
        supplied = (x_api_key or "").encode()
        if not secrets.compare_digest(supplied, api_key.encode()):
            raise HTTPException(status_code=401, detail="missing or invalid API key")

    protected = [Depends(require_key)]

    def unavailable(route: str) -> HTTPException:
        return HTTPException(status_code=503, detail=f"store unavailable ({route})")

    @app.get("/health")
    def health() -> dict[str, str]:
        metrics.api_requests.labels(route="/health").inc()
        if not store.healthy():
            raise unavailable("/health")
        return {"status": "ok"}

    @app.get("/events", dependencies=protected)
    def events(
        event_type: str | None = Query(default=None, alias="type", max_length=128),
        limit: int = Query(default=50, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        metrics.api_requests.labels(route="/events").inc()
        try:
            return [record.as_dict() for record in store.list_events(event_type, limit)]
        except StoreError as exc:
            raise unavailable("/events") from exc

    @app.get("/aggregates", dependencies=protected)
    def aggregates() -> dict[str, Any]:
        metrics.api_requests.labels(route="/aggregates").inc()
        try:
            return store.aggregates()
        except StoreError as exc:
            raise unavailable("/aggregates") from exc

    @app.get("/metrics")
    def scrape() -> Response:
        return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)

    return app


def app_from_env() -> FastAPI:
    """Application factory used by ``uvicorn --factory`` and ``streamforge serve``."""
    settings = Settings()
    configure_logging(settings.log_level)
    store, _ = build_stores(settings)
    key = settings.api_key.get_secret_value() if settings.api_key else None
    return create_app(store, api_key=key)
