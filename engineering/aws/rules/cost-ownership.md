---
id: cost-ownership
type: rule
clade: engineering
subclade: aws
title: Every AWS Resource Has an Owner and a Budget Signal
statement: Every AWS resource that takes tags carries the project's owner tag, that key is a cost allocation tag, and its account has a budget alerting on forecast spend.
enforcement: judgment
references:
  - docs/cost.md
---

# Every AWS Resource Has an Owner and a Budget Signal

Spend on AWS is attributed to someone and watched by something. A resource whose owner nobody can name cannot be right-sized or turned off, and an account with no budget learns about a runaway cost from the invoice.

This is the part of the Well-Architected cost pillar a single change can be held to — `COST03-BP02 Add organization information to cost and usage` and `COST02-BP05 Implement cost controls`. [`docs/cost.md`](../docs/cost.md) argues why the rule stops there, what AWS does and does not enforce for tags, and why no dollar figure from the predecessor survives.

## Conditions

1. **Every resource the change creates that accepts tags carries the project's owner tag key with a non-empty value.** The project names the key once (for example `owner`) in its own configuration, and every resource uses it. Decided before deployment by review of the infrastructure code — no generic tag check was found in Checkov or cdk-nag — and after deployment by the AWS Config rule `required-tags`, with `tag1Key` set to the project's key, for the resource types that rule covers. An AWS Organizations tag policy is not a detector for this condition, because AWS states that untagged resources are not evaluated by it.
2. **The owner tag key is activated as a user-defined cost allocation tag.** AWS: "For tags to appear on your billing reports, you must activate them" ([Activating user-defined cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)). Decided by review of the account's billing configuration, once, when the key is introduced.
3. **The account the change deploys to has an AWS Budgets cost budget with an alert on forecasted spend.** A forecast alert reports before the money is spent; an alert on actual spend alone reports after. The amount and the threshold are the project's. Decided by review, once per account; a change that creates an account creates its budget.

## Where this stops

**No figure here.** The rule requires an owner, an activated key and a forecast alert; it sets no budget amount, alert percentage, tag set beyond the owner key, or cost ceiling for a design. Those are the project's, and the predecessor's figures had no source.

**Account-wide reviews are not a change.** Right-sizing with Compute Optimizer, buying Savings Plans, decommissioning idle resources and reading Cost Anomaly Detection are periodic work on a running estate; [`docs/cost.md`](../docs/cost.md) covers them and no condition does.

**Resources AWS creates on the workload's behalf** — a service-linked role, an ENI a service attaches — are not the change's to tag, and Config's covered-type list is where the condition stops after deployment.

**Who pays across a client's accounts** is client logic (`ahrena-engineering-fundamentals:rules/client-logic.md`).
