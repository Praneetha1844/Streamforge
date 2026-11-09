# Configuration reference

Streamforge reads settings from environment variables with the `SF_` prefix. A `.env` file in
the working directory is read as well, and real environment variables win over it.
`.env.example` lists every variable. Invalid values stop the program at start-up with exit
code 2 and a message naming the setting.

## Application settings

| Variable | Default | Allowed values | Meaning |
|---|---|---|---|
| `SF_QUEUE_BACKEND` | `local` | `local`, `pubsub` | Where messages come from. `local` is an in-process queue for tests and demos. |
| `SF_STORE_BACKEND` | `memory` | `memory`, `postgres` | Where events and dead letters are kept. |
| `SF_DATABASE_URL` | none | PostgreSQL URL | **Required** when the store is `postgres`. Treated as a secret and never logged. |
| `SF_PUBSUB_PROJECT` | none | GCP project ID | **Required** when the queue is `pubsub`. |
| `SF_PUBSUB_TOPIC` | none | topic name | **Required** when the queue is `pubsub`. Name only, not the full path. |
| `SF_PUBSUB_SUBSCRIPTION` | none | subscription name | **Required** when the queue is `pubsub`. Name only, not the full path. |
| `SF_SCHEMA_DIR` | `schemas` | directory | Folder of `<type>.v<N>.json` schema files, loaded at start-up. |
| `SF_RULES_PATH` | `quality/rules.yaml` | file | Data-quality rules used by `streamforge quality`. |
| `SF_MIGRATIONS_DIR` | `migrations` | directory | SQL migrations used by `streamforge migrate`. |
| `SF_MAX_DELIVERY_ATTEMPTS` | `5` | integer, 1 or more | Delivery attempts before a persistent store failure is dead-lettered as `SINK_FAILURE`. |
| `SF_BATCH_SIZE` | `100` | integer, 1 to 1000 | Messages pulled per batch. |
| `SF_POLL_INTERVAL_SECONDS` | `1.0` | number, greater than 0 | Wait between polls when the queue is empty (`run --follow`). |
| `SF_METRICS_PORT` | `9100` | 1 to 65535 | Port of the worker's Prometheus endpoint. |
| `SF_API_HOST` | `127.0.0.1` | host or address | Bind address of the read API. Use `0.0.0.0` inside a container. |
| `SF_API_PORT` | `8000` | 1 to 65535 | Port of the read API. |
| `SF_API_KEY` | none | any string | Optional. When set, `/events` and `/aggregates` require it in the `X-API-Key` header. Treated as a secret. |
| `SF_LOG_LEVEL` | `INFO` | standard Python level names | Log verbosity. Logs are JSON lines on stdout. |

Rules between settings:

- `SF_STORE_BACKEND=postgres` needs `SF_DATABASE_URL`.
- `SF_QUEUE_BACKEND=pubsub` needs all three `SF_PUBSUB_*` settings.
- Keep `SF_MAX_DELIVERY_ATTEMPTS` below the Pub/Sub subscription's own limit
  (`max_delivery_attempts` in the Terraform, default 10), so the application records a reason
  code before Pub/Sub gives up.

## Docker Compose variables

These are read by `docker-compose.yml`, not by the application.

| Variable | Meaning |
|---|---|
| `POSTGRES_PASSWORD` | Password of the local database. Required. Use URL-safe characters, it is embedded in a connection URL. |
| `GRAFANA_ADMIN_PASSWORD` | Admin password of the local Grafana. Required. |

## Typical combinations

| Goal | Settings |
|---|---|
| Try it on a laptop | defaults, then `streamforge run --demo 200` |
| Local stack with a real database | `SF_STORE_BACKEND=postgres`, `SF_DATABASE_URL=...`, then `streamforge migrate` |
| Deployment on GCP | `SF_QUEUE_BACKEND=pubsub`, `SF_STORE_BACKEND=postgres`, the `SF_PUBSUB_*` settings, `SF_DATABASE_URL` from a secret manager |

## Notes

- Secrets (`SF_DATABASE_URL`, `SF_API_KEY`) are held as secret values, so they do not appear in
  settings representations or logs. Pass them through your platform's secret store, not
  through files in the repository.
- The read API and the worker are separate processes. With the in-memory store they do not
  share data. Use `postgres` when both are running.
