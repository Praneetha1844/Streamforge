# Development guide

## Setup

Python 3.12 or newer.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev,postgres,pubsub,otel]"
pre-commit install
```

The `postgres`, `pubsub` and `otel` extras are optional at runtime. Install them to run the
whole test suite, because the adapter tests are skipped when the libraries are missing.

## Make targets

| Target | What it runs |
|---|---|
| `make lint` | `ruff check` and `ruff format --check` |
| `make format` | `ruff check --fix` and `ruff format` |
| `make typecheck` | `mypy` in strict mode over `src/streamforge` |
| `make test` | `pytest` with a coverage report |
| `make check` | lint, typecheck and test, the same as CI |
| `make demo` | `streamforge run --demo 200 --seed 7` |
| `make up` / `make down` | the Docker Compose stack |
| `make tf-check` | `terraform fmt`, `init -backend=false` and `validate` |

## Project layout

```
src/streamforge/
  domain.py         envelope, Record, DeadLetter, reason codes, errors
  ports.py          Queue, EventStore, DeadLetterStore, Message
  registry.py       schema registry
  transform.py      pure payload transforms
  pipeline.py       Processor and replay
  quality.py        data-quality rules
  adapters/         local queue, Pub/Sub, in-memory store, PostgreSQL
  api.py  cli.py  bootstrap.py  config.py  metrics.py  tracing.py  logging_setup.py
  generator.py  migrate.py
tests/              one test module per source module, plus adapter tests
```

Dependencies point inward: the core knows the ports and never an adapter. Only
`bootstrap.py` imports adapters.

## Tests

- Tests use the in-memory adapters and `tests/conftest.py` builds the pipeline harness, so no
  network or database is needed.
- The Pub/Sub and PostgreSQL adapter tests use fakes or patch the client library. They check
  error handling and message wrapping, not real service behaviour.
- There are **no integration tests** against a real broker or database yet.

| Area | Test module |
|---|---|
| Envelope and records | `test_domain.py` |
| Schema registry | `test_registry.py` |
| Transforms | `test_transform.py` |
| Processing, retries, dead letters, replay | `test_pipeline.py` |
| Queues and stores (in memory) | `test_adapters.py` |
| Pub/Sub adapter | `test_pubsub_queue.py` |
| PostgreSQL adapter | `test_postgres_store.py` |
| Quality rules | `test_quality.py` |
| Read API | `test_api.py` |
| Command line | `test_cli.py` |
| Settings | `test_config.py` |
| Migrations | `test_migrate.py` |
| Generator | `test_generator.py` |

## Adding an event type

1. Add `schemas/<type>.v1.json` (JSON Schema draft 2020-12). Never edit a published version.
2. If the stored payload needs derived fields, write a pure function in `transform.py` and
   register it in `default_transforms()`.
3. Add tests: a valid event is stored, an invalid one is dead-lettered as `SCHEMA_VIOLATION`.
4. Add quality rules in `quality/rules.yaml` if the data has invariants worth checking.
5. Document the type in [DATA_CONTRACTS.md](DATA_CONTRACTS.md).

## Adding an adapter

1. Implement the relevant port from `ports.py` (`Queue`, `EventStore`, `DeadLetterStore`).
2. Raise `StoreError` or `QueueError` for operational failures, never raw client exceptions,
   and keep connection details out of the message.
3. Select it in `bootstrap.py` from a new setting value in `config.py`, importing the client
   library lazily so the core still runs without it.
4. Add the library as an optional extra in `pyproject.toml` and test the error handling.

## Conventions

- Line length 100, `ruff` for lint and format, `mypy --strict` for the package.
- Conventional commit messages (`feat`, `fix`, `docs`, `test`, `build`, `ci`, `chore`).
- Keep the core free of I/O. Side effects belong to adapters and the CLI.
- Never log payload values. Log ids, reason codes and counts.

## Glossary

| Term | Meaning |
|---|---|
| Event | A JSON message with an envelope and a payload |
| Envelope | `id`, `type`, `source`, `schema_version`, `occurred_at`, `payload` |
| Schema registry | The directory of versioned JSON Schemas |
| Idempotent write | Writing the same event twice leaves one stored record |
| Dead letter | A raw message that could not be processed, kept with a reason code |
| Replay | Re-publishing dead letters after the cause is fixed |
| Ack / nack | Telling the queue a message is done, or should be redelivered |
| Port / adapter | An interface the core depends on, and a concrete implementation of it |
