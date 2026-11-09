# ADR 0005: Forward-only SQL migrations with a minimal runner

Status: accepted

## Context

The schema is two tables. A full migration framework is more machinery than this needs, but
schema changes still have to be repeatable, ordered and recorded.

## Decision

Migrations are plain SQL files named `NNN_description.sql`, applied in name order by a small
runner. Applied versions are recorded in `schema_migrations`. Each migration runs in its own
transaction. There are no down-migrations. Changes follow expand then contract.

## Consequences

- Easy to read, review and run by hand with `psql`.
- No rollback script. Recovery from a bad migration is a backup restore or a corrective
  forward migration.
- Two runners at once are not coordinated. Run migrations from a single place.
- If the schema grows or needs branching or data migrations, move to Alembic or Flyway.
  The file naming makes that migration straightforward.

## Alternatives considered

- **Alembic** or **Flyway** are capable but heavier than two tables justify.
- **Create tables on application start** hides schema changes and is unsafe with several instances.
