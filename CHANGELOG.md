# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Optional `SF_API_KEY` protecting `/events` and `/aggregates`.
- Configuration, command-line and API references, a development guide, a roadmap, a
  documentation index and a security policy.
- Tests for the Pub/Sub and PostgreSQL adapters using fakes.
- Project URLs, classifiers and the `py.typed` marker.

### Fixed
- `replay` no longer deletes dead letters into the in-process queue, which would lose them.
- Pub/Sub acknowledgement, nack and publish-timeout failures are raised as `QueueError`.
- A one-shot `run` exits with code 1 on a queue error instead of retrying forever.
- Invalid `generate` arguments exit with code 2 instead of a traceback.
- `quality` warns when it ran against an empty store.
- Terraform enables the Resource Manager and IAM APIs, and the password rotation command names
  the module path.
- The freshness rule's comment now describes what it measures.

### Changed
- Docker images use the `slim-bookworm` base, carry image labels, and the Compose API service
  has a health check.
- CI caches pip by `pyproject.toml`, cancels superseded runs and can be started manually.

## [0.1.0] - 2026-11-10

### Added
- Event envelope, file-based schema registry and per-type JSON Schema validation.
- Composable, pure transformation pipeline.
- Processor with at-least-once delivery, idempotent writes, retry and dead-letter handling.
- Adapters: in-process queue, Google Pub/Sub queue, in-memory store, PostgreSQL store.
- FastAPI read API (`/events`, `/aggregates`, `/health`, `/metrics`).
- Prometheus metrics, optional OpenTelemetry spans and structured JSON logs.
- YAML-defined data-quality rules and report.
- SQL migrations with a minimal runner, seeded synthetic event generator, replay CLI.
- Terraform for Pub/Sub, Cloud SQL, Cloud Run and Artifact Registry (not applied).
- Docker Compose stack with Prometheus and Grafana provisioning.
