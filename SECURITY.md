# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/Praneetha1844/Streamforge/security/advisories/new)
for this repository. Do not open a public issue for a security problem. Include what you
found, how to reproduce it and which version or commit it affects.

This is a personal project maintained by one person. There is no service level agreement,
but reports are read and answered as soon as practical.

## Scope

In scope: the code in this repository, its Docker and Compose files and the Terraform.

Out of scope: vulnerabilities in third-party dependencies (report them upstream), and
problems in a deployment's own configuration.

## Status and known limits

Streamforge has not been run in production or independently reviewed. Read the
**Limitations** section of the [README](README.md) before depending on it. Points that matter
for security:

- The read API has no authentication unless `SF_API_KEY` is set, and then only one shared
  key. Keep it behind internal ingress.
- Dead-letter details and logs can contain values from rejected payloads. Restrict access to
  the `dead_letters` table and to logs.
- The generated database password is stored in Terraform state. Use a private remote
  backend.
- Dependencies are not pinned to exact versions or scanned automatically.

## Handling secrets

Never commit `.env` files, Terraform state or `terraform.tfvars` with real values. If a
secret is committed by mistake, rotate it first, then remove it. Removing it from history
alone does not make it safe.
