---
id: exposure
type: doc
clade: engineering
subclade: gcp
title: What a Google Cloud Error Carries
summary: Why an error from a Google Cloud client library is not a message for a caller, what identifiers it and the platform's resource names carry, where they leak from an application, and the shape of the translation that keeps them inside.
references:
  - rules/exposure.md
  - docs/identity-and-access.md
---

# What a Google Cloud Error Carries

This is the companion to [`rules/exposure.md`](../rules/exposure.md), the Google Cloud form of the framework's vendor-agnostic exposure rule, [`layer-exposure.md`](../../security/rules/layer-exposure.md) (nothing sensitive leaves the layer that owns it). That rule says what is sensitive and what an exit is; this document says what is sensitive in a Google Cloud deployment specifically, and where it comes from. Pages were read on 2026-11-14.

## The incident this answers

A product built with the agency returned a cloud SDK's access-denied message, verbatim, in an HTTP 500 body. From that one response a client's engineer read the cloud account, the role the service ran as, the permission that was denied, the path where a third party's credential was stored, and the existence of a permissions boundary. The incident was on another vendor; the same handler on Google Cloud leaks the same things, because the vendor's errors are written for the developer who called the API, not for the developer's caller.

## What a Google Cloud error is built to carry

Google's APIs follow AIP-193. The `Status.message` is a developer-facing English text, meant to be actionable; request-specific values go in an `ErrorInfo` detail with a `reason`, a `domain` (the service, for example `pubsub.googleapis.com`) and a `metadata` map ([AIP-193](https://google.aip.dev/193)). A client library surfaces both. Everything in them is written for the principal that called the API, which is the application's own service account, and none of it is filtered for whoever called the application.

Concretely, an access-denied error names the principal and the permission. Cloud Storage's troubleshooting page shows the shape: the service account's email followed by "does not have storage.objects.get access to" the object ([Cloud Storage troubleshooting](https://docs.cloud.google.com/storage/docs/troubleshooting)). A service account's email contains the project ID (`name@PROJECT_ID.iam.gserviceaccount.com`), so the message that names the principal names the project too.

## What a Google Cloud identifier locates

A full resource name is `//SERVICE/` followed by the resource's path, and for nearly every resource the path starts with the project ID: `//cloudresourcemanager.googleapis.com/projects/PROJECT_ID`, `//run.googleapis.com/projects/PROJECT_ID/locations/LOCATION_ID/services/SERVICE_ID`, `//iam.googleapis.com/projects/PROJECT_ID/serviceAccounts/SERVICE_ACCOUNT_EMAIL` ([Full resource names](https://docs.cloud.google.com/iam/docs/full-resource-names); [AIP-122](https://google.aip.dev/122)).

The project ID is permanent, globally unique, and appears in the name of many other resources; the vendor notes that referencing a project or its resources exposes the project ID and resource name, and asks that no sensitive information be put in a project name, project ID or other resource name ([Creating and managing projects](https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects)). The same page's warning is repeated for labels, which "are not designed to handle sensitive information" ([Labels overview](https://docs.cloud.google.com/resource-manager/docs/labels-overview)).

A project ID is not a secret, and leaking one does not grant access. It is the first coordinate of every other identifier: with it, a reader knows which project to probe, which service account names to try in a phishing message, which bucket names to guess. The exposure rule treats it as infrastructure detail, the same class as a role, a policy or a network layout.

So the sensitive classes, in a Google Cloud deployment, are:

| Class | What it looks like on Google Cloud |
|---|---|
| an access policy or binding | an allow or deny policy, a binding of `roles/...` to a `serviceAccount:`, `user:` or `group:` member, an IAM Condition |
| an identity | a service account email, a workload identity pool or provider name, a principal set |
| an account-level identifier | an organization ID, folder ID, project ID or project number, a billing account ID |
| a resource path | a full or relative resource name: `projects/.../secrets/...`, `projects/.../locations/.../services/...`, a bucket and object name, a Cloud SQL connection name `PROJECT:REGION:INSTANCE` |
| network layout | a VPC, subnet or range, an internal IP or hostname, a firewall rule, a VPC Service Controls perimeter name |
| the provider's error | `Status.message`, `ErrorInfo` metadata, a stack trace from a client library, a whole HTTP body from a Google API |

## Where it leaks from

- **A response.** The handler catches the client library's exception and returns its message, or serialises the exception, or wraps it in its own error whose text interpolates it.
- **A log the caller can read.** A log line goes to Cloud Logging, which is internal, but the same line is also written to a response, a client-side console, or a support ticket. Inside the project, Cloud Logging is the right place for the detail, with access restricted: the audit-logging best practices ask for least privilege on log access and allow field-level access controls to hide fields such as an email ([Audit logging best practices](https://docs.cloud.google.com/logging/docs/audit/best-practices)).
- **Error Reporting.** It groups errors parsed from logs, with context such as the request URL and user ([Formatting error messages](https://docs.cloud.google.com/error-reporting/docs/formatting-error-messages)). That is internal and is where the detail belongs; it becomes an exit only when its content is copied outward.
- **An infrastructure output.** A Terraform output, a deployment script's echo, or a CI log that prints a policy, a key or a whole resource. The vendor-neutral side of that is the Terraform plugin's (issue 295 of this repository).

## The translation

The correction is the one the vendor-agnostic rule names: at the boundary where the application answers its caller, a caught Google Cloud error becomes the application's own error, with a code from the application's contract, a generic message, and a correlation identifier; the detail goes to an internal log, by named fields taken from the error (type, reason, domain, status), with no secret, no message text and no policy, binding or service account email in it.

What the caller learns from the code is what the caller can act on: the request was refused, the resource does not exist for this caller, the service is unavailable and the request can be retried. AIP-193 makes the same choice for Google's own APIs, in the other direction: an API returns `PERMISSION_DENIED` before checking existence, so that a caller without access cannot learn whether a resource exists ([AIP-193](https://google.aip.dev/193)). An application that passes the provider's message through gives its caller more than Google gives the application.

## Where this stops

This document does not define the sensitive classes in general or the list of exits; the vendor-agnostic rule does. It does not cover how each language writes the translation: that is each language plugin's, under item 10 of the owner's directive on epic 285. Personal and payment data in an application's own records are read by `ahrena-engineering-security:skills/reviewing-sensitive-data/SKILL.md`, not here.
