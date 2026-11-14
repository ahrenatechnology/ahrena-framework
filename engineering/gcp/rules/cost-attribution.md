---
id: cost-attribution
type: rule
clade: engineering
subclade: gcp
title: Attributable Spend on Google Cloud
statement: On Google Cloud, every billable resource a change creates carries an owner label, and the project it bills to has a budget whose alerts reach a person.
enforcement: judgment
references:
  - docs/cost.md
---

# Attributable Spend on Google Cloud

Spend nobody owns is spend nobody weighs, and a bill nobody is warned about arrives as a surprise. Two conditions. [`docs/cost.md`](../docs/cost.md) cites the Google Cloud pages behind both and explains why a budget is a signal and not a cap.

## Conditions

1. **An owner label on every billable resource.** Each resource a change creates that accepts labels (a Cloud Run service or job, a VM, a disk, a bucket, a Cloud SQL or AlloyDB instance, a Pub/Sub topic or subscription, a BigQuery dataset, a GKE cluster) carries a label whose key is the installation's owner key, `owner` unless the installation names another, and whose value is a team or cost centre, never a person's email or any other personal data. A label applied by a shared default that the resource inherits satisfies the condition as well as one written on the resource. Decided by a reviewer, and on the deployed project by grouping the billing export to BigQuery by that key, where unlabelled cost appears as an empty group.

2. **A budget that reaches a person.** A change that creates a project, or the first billable resource in a project that bills to no budget, adds or names a Cloud Billing budget that covers it, with threshold alerts delivered to a monitored recipient: a billing contact, or a Pub/Sub topic someone consumes. Decided by a reviewer.

## Where this stops

**A budget is not a cap**, and this rule does not ask for one. Removing billing on a budget notification stops every service in the project and may delete resources; whether a project may be shut off that way is its owner's decision.

**The amount, the thresholds and the label vocabulary are the client's.** This rule requires that an owner label and a budget exist, not what they say. The owner key, the cost centres and the amounts are recorded in the installation (`ahrena-engineering-fundamentals:rules/client-logic.md`); a change that cannot tell which owner value to use raises it as a question.

**Resources that do not take labels**, and costs that are not attributable to a resource (support, some network egress), are outside condition 1. They are attributed by project, which is why condition 2 is per project.

**Tags** may carry ownership where the organization enforces it by policy. Where they do, a tag satisfies condition 1 and the reviewer reads the tag instead of the label.

**Finding waste** (idle resources, rightsizing, commitments) is the owner's recurring work with Google's recommenders, not a condition of a change.
