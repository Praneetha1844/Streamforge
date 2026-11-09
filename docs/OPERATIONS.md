# Operations runbook

These procedures describe how the system is designed to be operated. They have not been
exercised against a deployed environment.

## Quick reference

| Task | Command |
|---|---|
| Apply database migrations | `streamforge migrate` |
| Run the worker | `streamforge run --follow` |
| Run the read API | `streamforge serve` |
| Evaluate data quality | `streamforge quality` |
| Replay dead letters | `streamforge replay [--reason CODE] [--limit N]` |
| Generate sample events | `streamforge generate --count 100 --seed 1` |

Configuration is read from `SF_*` environment variables. See `.env.example`.

## Health and signals to watch

| Signal | Concern |
|---|---|
| `streamforge_events_dead_lettered_total` rising | Producers sending bad data, or a schema or transform bug. Break down by `reason`. |
| `streamforge_events_retried_total` rising | The database is failing or slow. |
| `streamforge_processing_seconds` p95 rising | Database latency or an overloaded worker. |
| `streamforge_events_processed_total` flat while producers publish | The worker is down or not pulling. |
| API `/health` returns 503 | The event store is unreachable. |
| Pub/Sub backlog or oldest-message age growing | Workers are not keeping up. |
| Messages appearing in the Pub/Sub dead-letter topic | Application dead-lettering failed repeatedly, investigate the worker first. |

## Investigating dead letters

1. Count by reason: `SELECT reason, count(*) FROM dead_letters GROUP BY reason;`
2. Look at examples: `SELECT id, reason, detail, failed_at FROM dead_letters WHERE reason = 'SCHEMA_VIOLATION' ORDER BY id LIMIT 20;`
3. Decide what the cause is:

| Reason | Usual cause | Fix |
|---|---|---|
| `INVALID_ENVELOPE` | Producer bug or a foreign message on the topic | Fix the producer. Replaying will not help. |
| `UNKNOWN_SCHEMA` | Producer uses a type or version that is not registered | Add the schema, deploy, then replay. |
| `SCHEMA_VIOLATION` | Payload does not match its schema | Fix the producer, or correct the schema if it was too strict, then replay. |
| `TRANSFORM_ERROR` | A transform raised on valid-looking data | Fix the transform, deploy, then replay. |
| `SINK_FAILURE` | The database was down for longer than the retry limit | Restore the database, then replay. |

Detail text can include payload values. Restrict access to the `dead_letters` table.

## Replaying dead letters

Replay re-publishes the raw messages to the queue and then deletes them from the store.
Each message is deleted only after it is published, so an interruption cannot lose messages.
It can duplicate them, which the idempotent store absorbs.

```bash
# Replay one reason after the fix is deployed
streamforge replay --reason UNKNOWN_SCHEMA --limit 500

# Check the result
streamforge quality
```

Replay a small batch first and confirm it processes before replaying the rest. If the
cause is not fixed, replayed messages simply return to the dead-letter store with the same
reason. Replay needs the same queue settings as the worker (`SF_QUEUE_BACKEND=pubsub` plus
the project, topic and subscription). With the in-process queue, replay has no effect on a
separate worker process.

## Evolving a schema

1. Copy the current schema to `schemas/<type>.v<N+1>.json` and make the change. Do not edit
   the old file.
2. Add tests that cover both versions.
3. Deploy the new version of the worker and API **before** any producer emits `v<N+1>`.
4. Switch producers to the new version.
5. When no producer emits the old version, remove its schema file in a later release.

See [DATA_CONTRACTS.md](DATA_CONTRACTS.md) for what counts as a breaking change.

## Database migrations

Migrations are forward-only SQL files (`migrations/NNN_description.sql`) applied in order
by `streamforge migrate`. There are no down-migrations.

- Use expand then contract: add new columns or tables first, deploy code that uses them,
  and remove old ones in a later release.
- Take a backup or confirm point-in-time recovery before a migration that changes data.
- Two runners at the same time are not coordinated. Run migrations from one place.

## Rollback

| What went wrong | Action |
|---|---|
| Bad application release | Route traffic back to the previous Cloud Run revision (`gcloud run services update-traffic ... --to-revisions=<previous>=100`). Worker and API are stateless. |
| Bad schema or transform | Roll back the release. Messages dead-lettered meanwhile can be replayed once it is fixed. |
| Bad migration | There is no automatic down-migration. Restore from backup or point-in-time recovery, or write a corrective forward migration. |
| Bad infrastructure change | Revert the Terraform change and run `terraform plan` before `apply`. Deletion protection is on by default. |

## Backups and recovery

Cloud SQL backups and point-in-time recovery are enabled by the Terraform. Restore
procedures have not been rehearsed. Rehearse one before depending on them.

## Security notes

- The database URL comes from Secret Manager and is exposed to the container as an
  environment variable. It is never logged: settings use `SecretStr`.
- Database errors are reduced to the exception class name so connection details are not
  logged or stored.
- Cloud Run ingress is internal only, and no public invoker is granted.
- Rotate the database password with `terraform taint module.cloudsql.random_password.database`,
  apply, then restart the services so they read the new secret version.
