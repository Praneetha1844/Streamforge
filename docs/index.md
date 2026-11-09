# Streamforge documentation

| Document | Read it to |
|---|---|
| [README](../README.md) | Understand what Streamforge is and run it |
| [Architecture](ARCHITECTURE.md) | See the components, message flow, failure handling and GCP layout |
| [Data contracts](DATA_CONTRACTS.md) | Know the event envelope, schemas, stored records and quality rules |
| [Configuration](CONFIGURATION.md) | Look up every `SF_*` setting |
| [Command line](CLI.md) | Use `generate`, `run`, `replay`, `quality`, `migrate` and `serve` |
| [Read API](API.md) | Query events and aggregates |
| [Operations runbook](OPERATIONS.md) | Investigate dead letters, replay, migrate, roll back |
| [Development guide](DEVELOPMENT.md) | Set up, test, add an event type or an adapter |
| [Infrastructure](../infra/terraform/README.md) | Review the Terraform for GCP |
| [Roadmap](ROADMAP.md) | See what is not built yet |
| [Decision records](adr) | Understand why the design is the way it is |
| [Security policy](../SECURITY.md) | Report a vulnerability and read the known limits |

## Decision records

1. [At-least-once delivery with idempotent writes](adr/0001-at-least-once-with-idempotent-writes.md)
2. [Validate at the edge with a file-based schema registry](adr/0002-validate-at-the-edge-with-a-file-based-schema-registry.md)
3. [Dead-letter store with reason codes and replay](adr/0003-dead-letter-store-with-reason-codes-and-replay.md)
4. [Ports and adapters for local and cloud](adr/0004-ports-and-adapters-for-local-and-cloud.md)
5. [Forward-only SQL migrations](adr/0005-forward-only-sql-migrations.md)
