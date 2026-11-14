---
name: designing-on-gcp
description: Use when a capability is to be built or moved onto Google Cloud and the services, identities, network path and cost controls have not been chosen yet - a new service, a new data store, a new integration, a workload leaving another platform. Produces a design that names one service per problem with its reason, the identity each workload runs as and what it may do, how traffic reaches it, how errors leave it, and who owns its spend, every choice traced to this plugin's rules and docs.
type: skill
clade: engineering
subclade: gcp
references:
  - rules/identity-and-access.md
  - rules/data-protection.md
  - rules/exposure.md
  - rules/cost-attribution.md
  - docs/services.md
  - docs/architecture-framework.md
  - docs/identity-and-access.md
  - docs/networking.md
  - docs/exposure.md
  - docs/data-protection.md
  - docs/cost.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
---

# Designing on Google Cloud

The output is a design document the builders and the owner read before anything is provisioned: short, one decision per line, each with its reason. It holds no Terraform; the infrastructure is written from it afterwards.

## 1. Read what the installation already decided

When Hyperion runs this skill, its step 1 has done this: take its output and do not read again. Otherwise, run `ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md` for each concern the capability spans, for the names the design uses, and read the installation's records: its component map, `AGENTS.md` and `CLAUDE.md`, and its infrastructure code, for its projects and environments, the organization policies it enforces, its owner label key, its budgets, the identity its CI uses. Those are the client's decisions and the design inherits them (`ahrena-engineering-fundamentals:rules/client-logic.md`). What the installation does not say becomes a question in step 7, not an assumption.

Output: the constraints the design must live within, each with where it was read.

## 2. State the requirements that choose services

Write down, from the issue, the facts a service choice turns on: request-driven or run-to-completion, expected load and its shape, latency the user notices, data model and consistency, regions and residency, the availability the product promises, who calls it (the internet, internal services, a partner). A requirement the issue does not state is a question; do not size for a requirement nobody stated.

## 3. Choose one service per problem

For each problem the capability has, take the starting recommendation in `docs/services.md` and check its "when not" column against the requirements of step 2. Record the service, the reason, and, where you depart from the recommendation, which "when not" case applies. Prefer the managed service and the smallest one that meets the requirement, the two premises that page argues.

A problem the page has no row for (sending email, or a choice inside a row the row does not settle, such as whether a large upload goes through the service or straight to the bucket) is chosen on the same two premises, with its facts read from the vendor's page or recorded as a question; never from memory.

## 4. Give each workload an identity

For each workload, name its own service account and the predefined roles it needs, each on the narrowest resource (`rules/identity-and-access.md`, `docs/identity-and-access.md`). Name how anything outside Google Cloud authenticates, CI first: Workload Identity Federation, never a key unless the design records why none serves. Name what is public, if anything, and why. A public web application behind the load balancer still needs its invoker grant or an invoker check turned off (`docs/networking.md`), and `iam.allowedPolicyMemberDomains` refuses a grant to `allUsers`: record which the design uses, and the organization-policy check as `unchecked`.

## 5. Draw the path a request takes

From the caller to the data: the public door (load balancer and Cloud Armor, or none), the Cloud Run ingress setting of each service, including one called only by Cloud Tasks, Eventarc or Cloud Scheduler, whose ingress and authentication are read from the vendor's page or recorded as a question, the private path to databases and Google APIs, egress, and the administrative path (`docs/networking.md`). Mark which hops the platform encrypts and which the design must (`docs/data-protection.md`), and where each secret lives.

## 6. Decide what leaves, and who pays

For each entry point, name the error contract the caller sees and where the detail is logged, so that no Google Cloud error, identifier or layout reaches a caller (`rules/exposure.md`, `docs/exposure.md`). Name the owner label value for every resource and the budget that covers the project (`rules/cost-attribution.md`, `docs/cost.md`).

## 7. Walk the pillars and hand back

Read the design against the pillars of `docs/architecture-framework.md` that it touches: security, reliability and cost at least; performance and sustainability when the design picks regions or sizes capacity. Record each gap as a change to the design or as a question.

Hand back the design with three lists: the decisions (service, identity, path, error contract, owner and budget), each with its reason and the doc or page it traces to; the questions for the owner, each naming who answers it; and what the design deliberately leaves out, under `exclusions:` at the end of the result.

## When this skill does not apply

**A change to something already designed.** Adding a field or a route to an existing service is a build; the review reads it with `reviewing-gcp`.

**Writing the Terraform.** That follows the design and belongs to `ahrena-engineering-terraform` (issue 295).

**A failing deployment.** That is `diagnosing-gcp-deployments`.

**Organization structure** (folders, the landing zone, organization policies). It is the client's, recorded in the installation; this skill reads it and does not design it.
