# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
