from typing import Any

import pytest
from conftest import Harness, make_event
from fastapi.testclient import TestClient

from streamforge.api import create_app
from streamforge.domain import StoreError


@pytest.fixture
def client(harness: Harness) -> TestClient:
    harness.publish(make_event(id="o1"))
    harness.publish(make_event(id="o2", occurred_at="2026-02-01T00:00:00+00:00"))
    payment = {"payment_id": "pay-1", "order_id": "ord-1", "amount_cents": 700, "currency": "eur"}
    harness.publish(make_event(id="p1", type="payment.settled", payload=payment))
    harness.processor.process_batch(10)
    return TestClient(create_app(harness.store, harness.metrics))


def test_health_is_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_events_are_listed_newest_first(client: TestClient) -> None:
    body = client.get("/events").json()
    # o2 is newest; p1 and o1 share a timestamp, so the higher event id comes first.
    assert [e["event_id"] for e in body] == ["o2", "p1", "o1"]
    assert body[0]["payload"]["total_cents"] == 1250
    assert body[0]["occurred_at"].startswith("2026-02-01")


def test_events_filter_by_type_and_limit(client: TestClient) -> None:
    orders = client.get("/events", params={"type": "order.placed"}).json()
    assert [e["event_id"] for e in orders] == ["o2", "o1"]

    limited = client.get("/events", params={"type": "order.placed", "limit": 1}).json()
    assert [e["event_id"] for e in limited] == ["o2"]


@pytest.mark.parametrize("limit", [0, 501, "abc"])
def test_invalid_limit_is_rejected(client: TestClient, limit: Any) -> None:
    assert client.get("/events", params={"limit": limit}).status_code == 422


def test_aggregates(client: TestClient) -> None:
    assert client.get("/aggregates").json() == {
        "events_by_type": {"order.placed": 2, "payment.settled": 1},
        "order_total_cents_by_currency": {"USD": 2500},
    }


def test_metrics_endpoint_exposes_prometheus_text(client: TestClient) -> None:
    client.get("/health")
    text = client.get("/metrics").text
    assert "streamforge_events_processed_total 3.0" in text
    assert 'streamforge_api_requests_total{route="/health"} 1.0' in text


class DownStore:
    def healthy(self) -> bool:
        return False

    def list_events(self, event_type: str | None, limit: int) -> list[Any]:
        raise StoreError("down")

    def aggregates(self) -> dict[str, Any]:
        raise StoreError("down")


@pytest.mark.parametrize("path", ["/health", "/events", "/aggregates"])
def test_store_outage_returns_503(path: str) -> None:
    client = TestClient(create_app(DownStore()))  # type: ignore[arg-type]
    assert client.get(path).status_code == 503


@pytest.fixture
def locked_client(harness: Harness) -> TestClient:
    harness.publish(make_event(id="o1"))
    harness.processor.process_batch(10)
    return TestClient(create_app(harness.store, harness.metrics, api_key="s3cret"))


@pytest.mark.parametrize("path", ["/events", "/aggregates"])
def test_data_routes_require_the_api_key_when_one_is_set(
    locked_client: TestClient, path: str
) -> None:
    assert locked_client.get(path).status_code == 401
    assert locked_client.get(path, headers={"X-API-Key": "wrong"}).status_code == 401
    assert locked_client.get(path, headers={"X-API-Key": "s3cret"}).status_code == 200


def test_health_and_metrics_stay_open_when_a_key_is_set(locked_client: TestClient) -> None:
    assert locked_client.get("/health").status_code == 200
    assert locked_client.get("/metrics").status_code == 200


def test_non_ascii_key_is_rejected_without_an_error(locked_client: TestClient) -> None:
    response = locked_client.get("/events", headers={"X-API-Key": "café".encode()})
    assert response.status_code == 401
