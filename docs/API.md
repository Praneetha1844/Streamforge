# Read API reference

A small read-only HTTP API over the event store, built with FastAPI. Interactive OpenAPI
documentation is served at `/docs` while the API is running.

Base URL: `http://<SF_API_HOST>:<SF_API_PORT>`. Responses are JSON, except `/metrics`.

## Authentication

By default there is none, and the API is meant to sit behind internal ingress. If
`SF_API_KEY` is set, `/events` and `/aggregates` require it in the `X-API-Key` header
and answer `401` otherwise. `/health` and `/metrics` stay open for probes and scrapers.

```bash
curl -H "X-API-Key: $KEY" "http://localhost:8000/events?limit=2"
```

A single shared key is a basic control. It is not a replacement for network isolation or a
real identity layer.

## `GET /events`

Newest events first, ordered by `occurred_at` and then event id.

| Query parameter | Default | Rules |
|---|---|---|
| `type` | all | Event type, for example `order.placed`. At most 128 characters. |
| `limit` | `50` | 1 to 500. Anything else returns `422`. |

There is no offset or cursor yet (see [ROADMAP.md](ROADMAP.md)).

Example response (illustrative values):

```json
[
  {
    "event_id": "evt-7-00000012",
    "type": "order.placed",
    "source": "synthetic-generator",
    "schema_version": 2,
    "occurred_at": "2026-11-10T09:15:04+00:00",
    "processed_at": "2026-11-10T09:15:06.120000+00:00",
    "payload": {
      "order_id": "ord-7-00000012",
      "customer_id": "cus-0042",
      "currency": "EUR",
      "channel": "web",
      "items": [{"sku": "SKU-007", "qty": 2, "unit_price_cents": 1250}],
      "item_count": 2,
      "total_cents": 2500
    }
  }
]
```

`currency`, `item_count` and `total_cents` are produced by the pipeline, see
[DATA_CONTRACTS.md](DATA_CONTRACTS.md).

## `GET /aggregates`

Event counts per type and order totals per currency.

```json
{
  "events_by_type": {"order.placed": 2, "payment.settled": 1},
  "order_total_cents_by_currency": {"USD": 2500}
}
```

## `GET /health`

`200 {"status": "ok"}` when the store is reachable, otherwise `503`.

## `GET /metrics`

Prometheus text format for the API process (`streamforge_api_requests_total{route}`). The
worker exposes its own metrics on `SF_METRICS_PORT`, see
[ARCHITECTURE.md](ARCHITECTURE.md#observability).

## Errors

| Status | Meaning |
|---|---|
| `401` | `SF_API_KEY` is set and the header is missing or wrong |
| `422` | A query parameter is invalid, for example `limit=0` |
| `503` | The event store is unavailable. The body names the route, never connection details. |
