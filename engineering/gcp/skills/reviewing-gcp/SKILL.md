---
name: reviewing-gcp
description: Use when a change under review declares or grants something on Google Cloud (a Terraform google resource, a gcloud command, a Cloud Build, Cloud Run or Config Connector file) or when application code calls a Google Cloud client library or handles its errors. Reads the routed files against this plugin's rules - a basic role, a project-wide grant, a service account key, a public bucket or service, an open firewall, a provider error, project id or resource path returned to a caller, a resource with no owner label. Every finding names the condition.
type: skill
clade: engineering
subclade: gcp
references:
  - rules/identity-and-access.md
  - rules/data-protection.md
  - rules/exposure.md
  - rules/cost-attribution.md
  - docs/identity-and-access.md
  - docs/networking.md
  - docs/exposure.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Google Cloud

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` and the security disciplines have read the change for what holds on any cloud. This skill reads what needs a Google Cloud reader: the grant, the network door, the key, the identifier, the error from Google's own client.

The conditions are checklists in `references/`, identified by `GCI-n` for infrastructure and `GCA-n` for application code. A finding cites the identifier. Severity follows `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the installation first

This plugin ships its routes as a fragment, `review-routes.json` at the plugin root, which the router merges when it is passed with `--plugin-routes` or `ROUTE_REVIEW_FRAGMENTS` (`ahrena-engineering-quality:docs/review-routes.md`). Two routes select this skill: `gcp-infrastructure` and `gcp-application`. Read the files each fired on. On the infrastructure files, run this plugin's hook, `hooks/check-gcp-grants.py`, which decides the basic-role, key and public-principal literals of `rules/identity-and-access.md`; what it reported is settled, and the checklist reads what it cannot see.

Before the checklists, read what the installation has already decided: its owner label key, its budgets, the organization policies it enforces, the identity it uses in CI. A condition an enforced organization policy already refuses (a key, when `iam.disableServiceAccountKeyCreation` holds on the project) is not reported again, but say which policy settled it.

## 2. Open the checklists the route calls for

| Route | Reference |
|---|---|
| `gcp-infrastructure` | `references/infrastructure.md`, with `rules/identity-and-access.md`, `rules/data-protection.md`, `rules/cost-attribution.md` and `docs/networking.md` |
| `gcp-application` | `references/application.md`, with `rules/exposure.md` and `docs/exposure.md` |

A change that holds both opens both. A change to application code that does not touch a Google Cloud client or its errors does not reach this skill.

## 3. Read beyond the hunk

For a grant, find the resource it attaches to and every other binding on the same principal: a narrow role added beside an Editor binding left in place is still Editor. For an error path, follow the caught error to every place it can reach a response, including a shared error handler the diff does not show. For a resource, find the labels it inherits.

Read what the change replaced, from the base revision, before calling a changed line wrong.

## 4. Apply the routed conditions

Work condition by condition. For each candidate, give the scenario in Google Cloud terms: who gains what (anyone on the internet reads the bucket; the CI key opens the project to whoever reads the CI secrets; the caller learns the project ID and the secret's name), and what it should have been. A condition whose answer depends on the owner's intent, and which the installation does not settle (is this bucket meant to be public, which owner value applies), is a `question`. A condition only the deployed state can decide, such as whether an inherited constraint holds on the project, is `unchecked` with the vendor detector named, so the owner can run it.

Read each condition's `Exempt` line and drop what it excludes.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the condition identifier, and a correction that is an instruction: the line, what to replace, and with what. A `GCA-1` finding is blocking when its line is in the diff, whatever the error happens to carry today.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**Terraform as a language**: module structure, state, pinning, `terraform test`. That is `ahrena-engineering-terraform` (issue 295); this skill reads only what the Google Cloud resources grant and expose.

**Another cloud.** An AWS or Azure resource in the same change is read by that plugin's review skill.

**Application security that is not about Google Cloud.** Untrusted input, the application's own authorization, its users' personal data: the security disciplines own them.

**A design that has not been written yet.** Reviewing a proposal before code is `designing-on-gcp`.
