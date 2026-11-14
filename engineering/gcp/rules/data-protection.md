---
id: data-protection
type: rule
clade: engineering
subclade: gcp
title: Encrypted Data on Google Cloud
statement: On Google Cloud, a change encrypts every path the platform leaves to it, rotates each CMEK key it creates, and reads each secret from Secret Manager.
enforcement: judgment
references:
  - docs/data-protection.md
---

# Encrypted Data on Google Cloud

Google Cloud encrypts data at rest and most traffic in transit without being asked. These conditions cover what it leaves to the customer. [`docs/data-protection.md`](../docs/data-protection.md) cites the page behind each, and separates the default from the customer's share.

## Conditions

1. **A database connection is encrypted.** A Cloud SQL instance a change creates or edits sets its SSL mode to `ENCRYPTED_ONLY` or `TRUSTED_CLIENT_CERTIFICATE_REQUIRED`, or every client connects through the Cloud SQL Auth Proxy or a Cloud SQL language connector. Reported by the Security Command Center finding `SSL_NOT_ENFORCED`, and decided in the change by a reviewer.

2. **No plaintext path the platform does not encrypt.** A connection to a VM on an external IP address, and the hop from a load balancer to a backend that carries data a client relies on, use TLS configured by the change. Decided by a reviewer, with Connectivity Tests to trace the path.

3. **A customer-managed key rotates.** A Cloud KMS symmetric key a change creates has automatic rotation configured; the period is the owner's, because the vendor fixes none. Where the owner requires CMEK for a service, the resource names its key. Reported by `KMS_KEY_NOT_ROTATED` and the `*_CMEK_DISABLED` findings, enforced where the organization sets them by `gcp.restrictNonCmekServices` and `gcp.restrictCmekCryptoKeyProjects`, and decided in the change by a reviewer.

4. **A secret lives in Secret Manager, read per secret.** No credential is committed, baked into an image, written into a Terraform variable default or a deployment manifest, or held in a plain environment variable set by the change. The workload reads it from Secret Manager through the client library, or through the platform's secret reference where the platform offers only that route, pinned to a version in production. Access is `roles/secretmanager.secretAccessor` on that secret, not on the project. A committed credential is decided by `ahrena-engineering-security:skills/reviewing-secrets/SKILL.md`; the rest by a reviewer.

## Where this stops

**Encryption at rest is not a condition.** The platform encrypts every stored byte by default and a change cannot opt out, so a finding that asks for it asks for nothing. CMEK is a condition only where the owner requires it, which is the owner's decision recorded in the installation.

**The rotation period is not set here.** Cloud KMS gives 90 days as an example and recommends a regular schedule without fixing one; a number in this rule would be invented.

**Public buckets and datasets** are condition 5 of [`rules/identity-and-access.md`](identity-and-access.md), which owns every public grant.

**Classification** of what is confidential, and which regulation applies, is the client's, and `ahrena-engineering-security:skills/reviewing-sensitive-data/SKILL.md` reads how an application handles it.
