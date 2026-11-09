# ADR 0002: Validate at the edge with a file-based schema registry

Status: accepted

## Context

Bad data is cheapest to stop where it enters. Downstream tables, dashboards and quality
checks all assume the payload has the documented shape.

## Decision

Validate every message before it is transformed or stored. First the envelope (pydantic),
then the payload against a JSON Schema selected by `(type, schema_version)`. Schemas are
files in `schemas/` named `<type>.v<N>.json`, versioned in git and loaded at start-up.

## Consequences

- Schema changes are reviewed, tested and deployed like code.
- A schema is immutable once published. Changes create a new version
  (see [DATA_CONTRACTS.md](../DATA_CONTRACTS.md)).
- Invalid messages never reach the store. They are dead-lettered with a reason code.
- The registry is read at start-up, so schema changes need a deployment. There is no hot reload.
- Stored data from several versions of a type can coexist, so transforms and readers must
  tolerate that.

## Alternatives considered

- **A hosted schema registry** (for example Confluent) adds an operational dependency
  that is not justified at this scale.
- **Validate in the database** (constraints) catches too little and fails too late.
- **Validate on read** lets bad data in and pushes the cost to every consumer.
