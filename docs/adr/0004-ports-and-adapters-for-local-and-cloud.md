# ADR 0004: Ports and adapters for local and cloud backends

Status: accepted

## Context

The pipeline logic (validate, transform, retry, dead-letter) is where the bugs and the value
are. It should be testable without Pub/Sub or PostgreSQL, and the same code should run on a
laptop and on GCP.

## Decision

The core depends on three small interfaces defined in `ports.py`: `Queue`, `EventStore`
and `DeadLetterStore`. Each has an in-memory or in-process adapter (`LocalQueue`,
`InMemoryStore`, `InMemoryDeadLetters`) and a real one (`PubSubQueue`, `PostgresStore`).
`bootstrap.py` is the only place that chooses adapters, from settings. Real adapters are
imported lazily so the optional extras are only needed when used.

## Consequences

- The test suite runs the full pipeline with no network or containers, and can inject
  failures (a flaky store, a broken dead-letter store).
- Adding a backend (for example Kafka-compatible brokers or another database) means writing
  one adapter, not changing the core.
- The real adapters are not covered by the unit tests and are excluded from the coverage
  report. They need integration tests against real services. These are not written yet.
- `LocalQueue` is not shared between processes, so a multi-container local setup cannot use
  it as a broker. The Compose stack works around this with a self-generating demo worker.

## Alternatives considered

- **Call the Pub/Sub and PostgreSQL clients directly** is simpler at first but makes the
  failure paths hard to test.
- **A mocking library over the real clients** couples tests to client internals.
