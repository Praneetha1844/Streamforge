# Roadmap

Nothing here is built. Items are ordered by how much they would raise confidence in the
system.

## Verification

- Run the whole project once end to end (`make check`, `docker compose up`, `terraform plan`)
  and fix what it finds. Nothing in this repository has been executed yet.
- Integration tests for PostgreSQL and Pub/Sub using containers or the Pub/Sub emulator.
- Reproducible benchmarks with the method and hardware stated. No performance figures are
  published until they exist.
- Property-based tests for transforms and the quality rules.

## Reliability

- Concurrent message handling and a connection pool for PostgreSQL (today: one connection
  per call, a synchronous loop).
- A shared local broker adapter (Kafka-compatible) so separate containers can share a queue
  without Pub/Sub.
- Lease extension for slow batches on Pub/Sub.
- Handle a failed acknowledgement after a dead-letter write without creating a duplicate
  dead letter.

## API

- Cursor-based pagination for `/events` (today only `limit`, newest first).
- Rate limiting, and an identity layer in place of the single shared key.
- Filtering by time range and source.

## Data

- Schema compatibility checks in CI, and optional hot reload of schemas.
- Down-migrations or an Alembic/Flyway migration path, with locking between runners.
- Retention and archiving of events and dead letters.
- Redact payload values from dead-letter details instead of documenting the risk.

## Observability

- OpenTelemetry exporter configuration and trace propagation from producers.
- Alert rules for the signals in the runbook.

## Operations

- Apply the Terraform in a scratch project, then record what had to change.
- A budget alert and a teardown script for the scratch project.
- Rehearse a database restore.
