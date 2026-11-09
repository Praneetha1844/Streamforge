# ADR 0001: At-least-once delivery with idempotent writes

Status: accepted

## Context

Queues such as Pub/Sub deliver at least once. A worker can crash after storing a record and
before acknowledging it, and the message is then delivered again. Exactly-once delivery
across a queue and a database is not available without distributed transactions.

## Decision

Acknowledge a message only after the store has accepted the record, and make the write
idempotent: `upsert` inserts by `event_id` and does nothing if the row exists
(`INSERT ... ON CONFLICT (event_id) DO NOTHING` in PostgreSQL). The store returns whether
a new row was inserted, so the pipeline can count duplicates.

## Consequences

- Redelivery, replay and running several workers are safe.
- First write wins. A producer that needs to correct an event must emit a new id.
- Ordering is not preserved, and consumers must not rely on it.
- Producers must generate stable ids. An id that changes on retry defeats idempotency.

## Alternatives considered

- **Acknowledge before storing** loses events on a crash. Rejected.
- **Update on conflict** lets a stale redelivery overwrite newer data. Rejected for now.
- **Distributed transaction or outbox** adds complexity this system does not need.
