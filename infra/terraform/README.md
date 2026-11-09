# Streamforge infrastructure (Terraform, GCP)

> **Status: validated by design review only; not applied.** This configuration has not been
> run with `terraform plan` or `terraform apply` against a real project. Treat it as a
> reviewed starting point and run `terraform plan` before trusting it.

## What it creates

| Resource | Purpose |
|---|---|
| Artifact Registry repository | Container images for the API and worker |
| Pub/Sub events topic and worker subscription | Event ingestion with retry backoff |
| Pub/Sub dead-letter topic and inspection subscription | Safety net for messages Pub/Sub gives up on |
| Cloud SQL for PostgreSQL 16 (private IP) | Event and dead-letter storage |
| Secret Manager secret | Database connection URL |
| Cloud Run services (worker, API) | The two workloads, internal ingress only |
| Two service accounts | One per workload, least-privilege roles |
| Project service enablement | Required Google APIs |

## IAM model

| Principal | Granted | On |
|---|---|---|
| Worker service account | `roles/pubsub.subscriber` | the events subscription only |
| Worker and API service accounts | `roles/secretmanager.secretAccessor` | the database URL secret only |
| Pub/Sub service agent | `roles/pubsub.publisher` | the dead-letter topic |
| Pub/Sub service agent | `roles/pubsub.subscriber` | the events subscription |

No role is granted at project level. No `allUsers` or `allAuthenticatedUsers` binding exists,
and Cloud Run ingress is internal only, so the API is not reachable from the internet.
Producers need `roles/pubsub.publisher` on the events topic, which is granted outside this
configuration to whichever identity publishes.

## Prerequisites

1. A GCP project with billing enabled and permission to enable APIs.
2. A VPC and subnetwork in the chosen region with **private services access** configured
   (an allocated IP range and a service networking connection). Cloud SQL uses private IP
   only, and this configuration does not create the network.
3. A container image already pushed to Artifact Registry. Cloud Run cannot create a service
   from an image that does not exist. Apply once, push the image to the `registry_url`
   output, then set `api_image` and `worker_image` and apply again. The first apply can
   target the registry only: `terraform apply -target=module.registry`.
4. Terraform 1.6 or newer.

## Usage

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit values; the file is git-ignored
terraform init
terraform plan
terraform apply
```

For checks that need no credentials:

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

## State and secrets

- The generated database password is stored in Terraform **state** and in Secret Manager.
  Use a remote backend (see the commented `backend "gcs"` block in `versions.tf`) with a
  private, versioned bucket and restrict read access to it.
- `terraform.tfvars` is git-ignored. Never commit state or variable files with real values.
- Rotate the password by tainting `random_password.database` and re-applying.

## Safety and cost notes

- `deletion_protection` defaults to `true` for the database and Cloud Run services. Set it to
  `false` in `terraform.tfvars`, apply, and only then destroy.
- Cloud SQL is billed while it exists. The default tier is `db-custom-1-3840` in a single
  zone. Choose a smaller tier for experiments, and `REGIONAL` availability for production.
- The worker runs with `min_instances = 1` and always-allocated CPU, because it pulls from
  Pub/Sub continuously. That is a continuous cost.
- Backups and point-in-time recovery are enabled, and add storage cost.
- Set a budget alert on the project before applying anything.
- `terraform destroy` removes the database, its data and the Pub/Sub topics. Export what you
  need first.
- Pub/Sub retains unacknowledged messages for 7 days. Dead-letter subscriptions retain for 7 days.

## Delivery limits

The Pub/Sub dead-letter policy forwards a message after `max_delivery_attempts` (default 10).
The application dead-letters earlier (after `SF_MAX_DELIVERY_ATTEMPTS`, default 5) and records
a reason code. Keep the Pub/Sub limit higher than the application limit.
