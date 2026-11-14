---
id: cost
type: doc
clade: engineering
subclade: gcp
title: Cost on Google Cloud
summary: How cost is attributed on Google Cloud (labels, tags, the billing export), why a budget is a signal and not a cap, what Google's recommenders and discounts offer and what each commits the owner to, and the vendor page behind each.
references:
  - rules/cost-attribution.md
  - docs/architecture-framework.md
---

# Cost on Google Cloud

This is the companion to [`rules/cost-attribution.md`](../rules/cost-attribution.md). The rule asks two things of a change: that what it creates can be attributed to an owner, and that someone hears about spend before the invoice. This document explains the mechanisms behind both, and what the vendor offers beyond them. Pages were read on 2026-11-14 under `docs.cloud.google.com`.

The Well-Architected Framework's cost pillar names four principles: align spending with business value, foster cost awareness, optimize resource usage, and optimize continuously ([Cost optimization](https://docs.cloud.google.com/architecture/framework/cost-optimization)). Attribution is the precondition of the first two: spending that cannot be traced to an owner cannot be weighed against what it buys.

## Labels attribute cost

A label is a key-value pair on a resource, used to organize resources and manage cost. Labels are sent to Cloud Billing, can filter and group cost reports, and are exported to BigQuery with the usage. A resource holds up to 64 labels; keys are 1 to 63 characters and start with a lowercase letter, values up to 63; both use only lowercase letters, digits, underscores and dashes ([Labels overview](https://docs.cloud.google.com/resource-manager/docs/labels-overview)). The same page says labels are not designed for sensitive information, so an owner label names a team or a cost centre, never a person's email.

**Tags** are a different mechanism: resources defined at the organization or project, inherited by children, and usable in IAM Conditions and some organization policy conditions, which labels are not; they too support cost allocation and the billing export ([Tags overview](https://docs.cloud.google.com/resource-manager/docs/tags/tags-overview)). An organization that enforces ownership through policy uses tags; a label is the lighter, per-resource form that every billable resource accepts.

The billing export to BigQuery carries standard usage cost, detailed resource-level cost, pricing data and committed-use metadata ([Export Cloud Billing data to BigQuery](https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery)). It is where a label becomes an answer: cost grouped by `owner` over a month.

## A budget is a signal, not a cap

A Cloud Billing budget compares actual or forecast spend to an amount and alerts at thresholds, by default 50%, 90% and 100%, by email to billing administrators and, for automation, through a Pub/Sub topic. The page is explicit that an alerts-only budget does not cap usage or spending ([Create, edit, or delete budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets)).

Capping is possible and destructive: Google's example has a function receive the budget notification and remove billing from the project, which stops every service in it, may delete resources irretrievably, and can still overshoot because notifications are delayed ([Disable billing usage with notifications](https://docs.cloud.google.com/billing/docs/how-to/disable-billing-with-notifications)). That is an owner's decision for a sandbox, not a default for a product.

## Finding waste

Google's recommenders report idle VMs, disks, IP addresses, images and GKE clusters, idle or overprovisioned Cloud SQL instances, Cloud Run CPU allocation, and commitment opportunities ([Recommenders](https://docs.cloud.google.com/recommender/docs/recommenders)), under the umbrella Google calls Active Assist ([Active Assist](https://docs.cloud.google.com/recommender/docs/whatis-activeassist)). They are read on a schedule by the owner; this plugin does not apply them.

## Discounts and what they commit

| Mechanism | What it is | What it commits | Page |
|---|---|---|---|
| Sustained use discounts | automatic on eligible Compute Engine machine series used more than 25% of a billing month, up to 30% on some series (less on others) | nothing | [Sustained use discounts](https://docs.cloud.google.com/compute/docs/sustained-use-discounts) |
| Spot VMs | discounted capacity Google may preempt at any time, with no SLA | the workload must tolerate interruption | [Spot VMs](https://docs.cloud.google.com/compute/docs/instances/spot) |
| Resource-based committed use discounts | Compute Engine resources in a region for one or three years | cannot be cancelled after purchase | [Resource-based CUDs](https://docs.cloud.google.com/compute/docs/instances/signing-up-committed-use-discounts) |
| Spend-based committed use discounts | a spend level on Compute Engine, GKE, Cloud Run or a named service, for one or three years, bought at the billing account | the spend, for the term | [Committed use discounts](https://docs.cloud.google.com/docs/cuds) |

A commitment is a financial decision of the client's, taken from measured usage; a design records the usage it expects so that the decision can be made, and does not make it.

## Quotas are not a budget

Quotas limit how much of a resource a project may use and are usually adjustable; system limits are fixed ([Quotas overview](https://docs.cloud.google.com/docs/quotas/overview)). A quota can stop a runaway deployment, but it is sized for capacity, not for money, and nothing ties it to a budget.

## Where this stops

This document gives no price; Google's pricing pages are the source and change on their own schedule. It does not decide a client's cost centres, label vocabulary beyond the owner key, budget amounts or commitments: those are recorded in the client's installation (`ahrena-engineering-fundamentals:rules/client-logic.md`).
