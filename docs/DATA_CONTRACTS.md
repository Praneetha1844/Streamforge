# Data contracts

## Event envelope

Every message is a JSON object with exactly these fields. Unknown fields are rejected.

| Field | Type | Rules |
|---|---|---|
| `id` | string | 1 to 128 characters. Unique per event. Used as the idempotency key. |
| `type` | string | Dotted lower-case name, for example `order.placed`. |
| `source` | string | 1 to 128 characters. Name of the producing system. |
| `schema_version` | integer | 1 or greater. Selects the payload schema. |
| `occurred_at` | string | ISO 8601 timestamp **with a timezone**. Naive timestamps are rejected. |
| `payload` | object | Validated against `schemas/<type>.v<schema_version>.json`. |

## Event types

### `order.placed`

| Version | Payload fields | Notes |
|---|---|---|
| 1 | `order_id`, `customer_id`, `currency` (3 letters), `items[]` | `items` needs at least one entry |
| 2 | Everything in v1, plus optional `channel` (`web`, `mobile`, `store`) | Backward compatible for readers of stored data |

Each item has `sku`, `qty` (integer, at least 1) and `unit_price_cents` (integer, at least 0).

Fields added by the pipeline before storage:

| Field | Meaning |
|---|---|
| `currency` | Upper-cased |
| `item_count` | Sum of item quantities |
| `total_cents` | Sum of `qty * unit_price_cents` |

### `payment.settled`

| Version | Payload fields |
|---|---|
| 1 | `payment_id`, `order_id`, `amount_cents` (integer, at least 0), `currency` (3 letters, upper-cased on storage) |

## Stored record

| Column | Meaning |
|---|---|
| `event_id` | Primary key, copied from `id` |
| `type`, `source`, `schema_version` | Copied from the envelope |
| `occurred_at` | When the event happened, from the producer |
| `processed_at` | When Streamforge stored it |
| `payload` | The transformed payload |

## Compatibility rules

1. **Never change a published schema file.** Add a new version instead.
2. **Backward-compatible changes** (a new optional field) can ship as the next version.
   Consumers of stored data must ignore unknown payload fields.
3. **Breaking changes** (removing or renaming a field, changing a type) need a new version
   and a transform that maps the old shape if stored data must stay uniform.
4. Keep an old version registered until no producer emits it, then remove it. Messages
   with a removed version are dead-lettered as `UNKNOWN_SCHEMA`.
5. A new `type` needs a schema file and, if the payload needs changes, an entry in
   `default_transforms()`.

## Data-quality rules

Rules live in `quality/rules.yaml` and run with `streamforge quality`. The command exits
with status 1 if any rule fails.

| Type | Meaning | Parameters |
|---|---|---|
| `not_null` | Field is present and not null | none |
| `range` | Numeric value within bounds. Non-numbers and booleans fail. | `min`, `max` (at least one) |
| `unique` | No duplicate values. Missing values are ignored. | none |
| `freshness` | Timestamp no older than the limit, measured from evaluation time | `max_age_seconds` |

A rule can set `event_type` to apply only to records of that type. Fields use dotted paths
into the stored record, for example `payload.total_cents`.
