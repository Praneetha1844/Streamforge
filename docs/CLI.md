# Command-line reference

```
streamforge [--version] <command> [options]
```

All commands except `generate` read their settings from `SF_*` variables (see
[CONFIGURATION.md](CONFIGURATION.md)).

## Commands

### `generate`

Write synthetic events as JSON lines. The same arguments always produce the same events.

| Option | Default | Meaning |
|---|---|---|
| `--count N` | `100` | Number of events. Must be 0 or more. |
| `--seed N` | `1` | Random seed. Event ids include the seed, so different seeds never collide. |
| `--invalid-ratio R` | `0.0` | Fraction, from 0 to 1, of events that are deliberately corrupted. |
| `--out FILE` | stdout | Write to a file instead. |

### `run`

Pull messages, validate, transform and store them.

| Option | Default | Meaning |
|---|---|---|
| `--follow` | off | Keep polling. Without it the command exits when the queue is empty. |
| `--demo N` | `0` | Publish N synthetic events (about 5% invalid) before processing. With `--follow` this repeats every cycle. |
| `--seed N` | `1` | Base seed for demo events. |
| `--poll-interval S` | `SF_POLL_INTERVAL_SECONDS` | Seconds between empty polls. |
| `--no-metrics-server` | off | Do not start the Prometheus endpoint on `SF_METRICS_PORT`. |

`SIGINT` and `SIGTERM` stop the loop after the current batch. A queue error ends a one-shot run
with exit code 1. With `--follow` it is logged and retried after the poll interval.

### `replay`

Re-publish dead letters to the queue, deleting each one only after it was published.

| Option | Default | Meaning |
|---|---|---|
| `--reason CODE` | all | Only replay this reason: `INVALID_ENVELOPE`, `UNKNOWN_SCHEMA`, `SCHEMA_VIOLATION`, `TRANSFORM_ERROR` or `SINK_FAILURE`. |
| `--limit N` | `1000` | Maximum number of messages to replay. |

Replay refuses to run with `SF_QUEUE_BACKEND=local` (exit code 2), because the in-process queue
is discarded when the command exits and the replayed messages would be lost. Prints
`{"replayed": N}`.

### `quality`

Evaluate the rules in `SF_RULES_PATH` against stored events and print a JSON report.

| Option | Default | Meaning |
|---|---|---|
| `--limit N` | `10000` | Evaluate the newest N events. |

Exit code 1 if any rule fails. If the store holds no events a warning is printed to stderr,
because every rule then passes without checking anything.

### `migrate`

Apply pending SQL migrations from `SF_MIGRATIONS_DIR` to `SF_DATABASE_URL`. Prints
`{"applied": [...]}`. Forward-only.

### `serve`

Run the read API with uvicorn on `SF_API_HOST:SF_API_PORT`. See [API.md](API.md).

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | A quality rule failed, or a one-shot `run` hit a queue error |
| `2` | Invalid configuration or arguments, a missing `SF_DATABASE_URL` for `migrate`, or a refused `replay` |

## Examples

```bash
streamforge generate --count 20 --seed 3 --invalid-ratio 0.1 --out sample.jsonl
streamforge run --demo 200 --seed 7
streamforge run --follow --poll-interval 2
SF_STORE_BACKEND=postgres SF_DATABASE_URL=... streamforge migrate
streamforge replay --reason UNKNOWN_SCHEMA --limit 500
```
