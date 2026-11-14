---
id: data-protection
type: doc
clade: engineering
subclade: gcp
title: Data Protection on Google Cloud
summary: What Google Cloud encrypts without being asked and what it leaves to the customer, when a customer-managed key earns its cost, how secrets and database connections are kept out of reach, and which vendor tool reports each condition of the data rule.
references:
  - rules/data-protection.md
  - docs/identity-and-access.md
  - docs/networking.md
---

# Data Protection on Google Cloud

This is the companion to [`rules/data-protection.md`](../rules/data-protection.md). It separates what the platform already does from what a change must do, because the conditions of the rule are only the second half. Pages were read on 2026-11-14 under `docs.cloud.google.com`.

## At rest: done by default

Google Cloud encrypts customer data at rest by default, with AES-256 in all but a few legacy cases, under a key hierarchy in which each layer protects the one below ([Default encryption at rest](https://docs.cloud.google.com/docs/security/encryption/default-encryption), updated May 2024). Nothing in a change turns this on and nothing can turn it off, so the rule asks nothing of it.

## Customer-managed keys: when the owner needs control

A customer-managed encryption key (CMEK) in Cloud KMS is for when the owner must control the key: its location, protection level, rotation, use and destruction; must be able to destroy data by destroying the key; must log the key's administration and use; or must meet a regulation that requires one of these ([CMEK](https://docs.cloud.google.com/kms/docs/cmek)). It is not a stronger form of the default encryption; it is control over the key, paid for in operation.

Two organization policies hold CMEK in place where it is required: `gcp.restrictNonCmekServices` refuses a new resource of a listed service without a Cloud KMS key, and `gcp.restrictCmekCryptoKeyProjects` limits which projects keys may come from. Both act only on resources created after they are set, and the second alone does not guarantee CMEK, so the vendor advises both ([CMEK organization policies](https://docs.cloud.google.com/kms/docs/cmek-org-policy)).

Cloud KMS recommends rotating keys automatically on a regular schedule and gives "every 90 days" only as an example; it fixes no period, and automatic rotation is not available for asymmetric keys ([Key rotation](https://docs.cloud.google.com/kms/docs/key-rotation)). The rule therefore requires that rotation is configured and leaves the period to the owner. Security Command Center reports a key without rotation as `KMS_KEY_NOT_ROTATED`, and a resource without CMEK as `BUCKET_CMEK_DISABLED`, `SQL_CMEK_DISABLED`, `DISK_CMEK_DISABLED`, `DATASET_CMEK_DISABLED` and their siblings ([Vulnerability findings](https://docs.cloud.google.com/security-command-center/docs/concepts-vulnerabilities-findings)).

## In transit: done by default, except where it is not

Requests to Google Cloud services travel over TLS, and traffic between VMs on internal addresses inside a VPC or peered VPCs is encrypted automatically. Two paths are the customer's: a connection to a VM on an external IP address, which the customer must encrypt, and the hop from a load balancer to its backends, which is encrypted only when configured ([Encryption in transit](https://docs.cloud.google.com/docs/security/encryption-in-transit), updated April 2025).

Cloud SQL's default SSL mode accepts unencrypted and encrypted connections alike; `ENCRYPTED_ONLY` refuses anything but TLS and `TRUSTED_CLIENT_CERTIFICATE_REQUIRED` adds a client certificate. The vendor strongly recommends enforcing SSL on an instance with a public IP. Connections through the Cloud SQL Auth Proxy or a language connector are encrypted whatever the mode, with IAM deciding who may connect ([Configure SSL/TLS](https://docs.cloud.google.com/sql/docs/postgres/configure-ssl-instance); [Cloud SQL Auth Proxy](https://docs.cloud.google.com/sql/docs/postgres/sql-proxy)). Security Command Center reports `SSL_NOT_ENFORCED`, `PUBLIC_SQL_INSTANCE`, `SQL_PUBLIC_IP` and `SQL_NO_ROOT_PASSWORD` ([Vulnerability findings](https://docs.cloud.google.com/security-command-center/docs/concepts-vulnerabilities-findings)).

## Secrets

Secret Manager holds credentials as versioned secrets, with IAM deciding who may read each one ([Secret Manager overview](https://docs.cloud.google.com/secret-manager/docs/overview)). Its best practices, which the rule's conditions follow ([Secret Manager best practices](https://docs.cloud.google.com/secret-manager/docs/best-practices)):

- grant `roles/secretmanager.secretAccessor` on the secret, not on the project ([Access control](https://docs.cloud.google.com/secret-manager/docs/access-control));
- read the secret through the API or a client library rather than through the file system or an environment variable, which a debug endpoint or a dependency that logs the process environment can expose; on a serverless platform that only offers those routes, they remain acceptable;
- reference a version number rather than `latest` in production, and disable a version before destroying it;
- enable Data Access audit logs for secret access.

## Storage

Uniform bucket-level access turns Cloud Storage ACLs off so only IAM grants access, and the vendor recommends it in general. Public access prevention makes requests from `allUsers` and `allAuthenticatedUsers` fail, and is inherited from the organization through `storage.publicAccessPrevention` ([Uniform bucket-level access](https://docs.cloud.google.com/storage/docs/uniform-bucket-level-access); [Public access prevention](https://docs.cloud.google.com/storage/docs/public-access-prevention)). Both are conditions of [`rules/identity-and-access.md`](../rules/identity-and-access.md) as much as of data protection, and that rule carries them.

## Finding sensitive data that is already stored

Sensitive Data Protection discovers, classifies and de-identifies sensitive data, by masking, redaction, bucketing, date shifting or tokenization ([Sensitive Data Protection overview](https://docs.cloud.google.com/sensitive-data-protection/docs/sensitive-data-protection-overview); [De-identifying sensitive data](https://docs.cloud.google.com/sensitive-data-protection/docs/deidentify-sensitive-data)). It is the vendor's tool for answering "where is the personal data" after the fact; it does not replace keeping the data out of a place it does not belong.

## Where this stops

What leaves an application through its responses, logs and errors is [`docs/exposure.md`](exposure.md). Network paths, private connectivity and VPC Service Controls are [`docs/networking.md`](networking.md). Which data a client classifies as confidential, and which regulation binds it, is that client's decision and is not platform content.
