# ADR 0003: Dead-letter store with reason codes and replay

Status: accepted

## Context

Some messages can never succeed: malformed JSON, an unknown schema, a payload that breaks
its schema. Redelivering them forever blocks capacity and hides real problems. Dropping
them loses data.

## Decision

The processor writes such messages to a dead-letter store with the raw bytes, a reason
code (`INVALID_ENVELOPE`, `UNKNOWN_SCHEMA`, `SCHEMA_VIOLATION`, `TRANSFORM_ERROR`,
`SINK_FAILURE`), a detail text and a timestamp, then acknowledges the original. If the
dead-letter write itself fails, the message is negatively acknowledged instead, so it is
never lost. A replay command re-publishes selected dead letters and deletes each one only
after publishing it.

The Pub/Sub dead-letter policy remains as a safety net with a higher attempt limit than the
application's, so the application gets to record the reason first.

## Consequences

- Failures are visible, countable by reason and recoverable.
- Dead letters hold raw payloads, so they need the same access control as the data.
- Detail text can echo values from the payload (schema library messages do).
  Envelope errors are built without input values.
- Replay can create duplicates. This is acceptable because writes are idempotent
  ([ADR 0001](0001-at-least-once-with-idempotent-writes.md)).
- Replaying without fixing the cause just re-creates the same dead letters.

## Alternatives considered

- **Pub/Sub dead-letter topic only** loses the reason and needs separate tooling to inspect.
- **Drop and log** loses data.
- **Block the queue** on a poison message stops everything behind it.
