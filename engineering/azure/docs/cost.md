---
id: cost
type: doc
clade: engineering
subclade: cloud
title: Cost on Azure
summary: Why every resource carries an owner tag and every workload scope a budget, how tags and Cost Management actually behave (no inheritance, plain text, a day's latency, budgets that only notify), and the optimisations the Well-Architected Cost Optimization pillar and Azure Advisor offer beyond the rule.
references:
  - rules/cost-attribution.md
---

# Cost on Azure

The companion of [`rules/cost-attribution.md`](../rules/cost-attribution.md). The rule asks for two signals, an owner and a budget; this says why those two, and how Azure's own tools behave when they carry them. Pages read on 2026-11-14.

The Well-Architected Cost Optimization pillar has fourteen checklist items, CO:01 *Create a culture of financial responsibility* to CO:14 *Consolidate resources and responsibility* ([Cost Optimization checklist](https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/checklist)). The rule covers the part of CO:03 *Collect and review cost data* and CO:04 *Set spending guardrails* that a reviewer can check on a change; the rest are design choices.

## An owner on every resource

CO:03 says each cost item should have a directly responsible individual as the resource owner ([Collect and review cost data](https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/collect-review-cost-data)). The framework carries that as a tag naming a team or a role, because a tag survives the person leaving and a personal name in a tag is personal data in plain text.

How tags behave, from [Use tags to organize your Azure resources](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/tag-resources):

- **Resources don't inherit the tags of their resource group or subscription.** A tag on the resource group does not answer "whose is this?" for the resource; that is why condition 1 asks for the tag on each resource.
- **Tags are stored as plain text** and the page says not to put sensitive values in them. [`rules/exposure.md`](../rules/exposure.md) condition 3 carries that.
- Each resource, resource group and subscription holds at most 50 tag name-value pairs; names are case-insensitive and values case-sensitive.

The Cloud Adoption Framework's tagging strategy groups example tags by purpose: functional (`app`, `env`, `tier`), classification (`criticality`, `confidentiality`), accounting (`costcenter`, `budget`, `department`) and ownership (`businessunit`, `opsteam`) ([Define your tagging strategy](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-tagging)). It names no tag `owner`; the framework leaves the name to the project and asks only that one exists and means ownership.

Azure Policy enforces it. *Require a tag on resources* and *Require a tag on resource groups* deny a request without the tag; *Inherit a tag from the resource group if missing* and *Add a tag to resources* add it with the `modify` effect without touching an existing value; existing resources are fixed with a remediation task ([Policy definitions for tagging](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/tag-policies)). Azure Policy evaluates a resource when it is created or updated and in a standard compliance cycle every 24 hours, and Microsoft recommends starting a new assignment with `audit` before switching to an enforcing effect ([Azure Policy overview](https://learn.microsoft.com/en-us/azure/governance/policy/overview)).

**Cost Management's tag inheritance is a different thing.** It applies subscription and resource group tags to child usage records, not to the resources, and takes about 8 to 24 hours to reach them; it is available for EA, MCA and MPA billing ([Tag inheritance](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/enable-tag-inheritance)). It is useful for a cost report and does not satisfy condition 1.

## A budget on every workload scope

A Cost Management budget notifies; it does not stop anything. Microsoft's tutorial says resources aren't affected and consumption isn't stopped. Budgets are evaluated every 24 hours against cost data that is typically available within 8 to 24 hours, and email notifications normally go out within an hour of evaluation. A budget takes up to five thresholds; at subscription and resource group scope an alert can trigger an action group, which is how a budget reaches an on-call channel or runs an automation. Budgets created with PowerShell don't send notifications ([Create and manage budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)).

Two consequences for the rule. A budget is a signal that arrives a day or more after the spend, so it bounds the size of a surprise, not its existence. And a budget whose alert reaches nobody is not a signal, which is why condition 2 asks for a recipient.

CO:03 suggests thresholds at 90%, 100% and 110% of target spend, and states an ingestion delay of 24 to 72 hours for actual cost data ([Collect and review cost data](https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/collect-review-cost-data)). The budgets tutorial says 8 to 24 hours. The two Microsoft pages disagree; the framework plans for the longer.

**Anomaly alerts** complement a budget: Cost Management checks each subscription daily against a forecast from the last 60 days, and an alert rule (at subscription scope only, five per subscription, email only) reports an anomaly when one is detected ([Identify anomalies and unexpected changes in cost](https://learn.microsoft.com/en-us/azure/cost-management-billing/understand/analyze-unexpected-charges)). A budget catches a slow overrun; an anomaly alert catches a sudden one. The framework recommends both and requires the budget.

## Ending what is not production

Condition 3 asks a non-production environment to say when it ends, because nothing in Azure removes it otherwise. A resource group that holds one experiment is deleted with it in one operation; a resource left in a shared group needs someone to find it. CO:08 *Optimize environment costs* is the pillar's item for this.

## Optimisations beyond the rule

These are not conditions; they are what a design review looks at once the signals exist.

- **Azure Advisor** recommends shutting down virtual machines and scale sets unused over the last seven days, and resizing ones whose load fits a cheaper SKU; its recommendations do not account for reservations or savings plans already bought ([Advisor cost recommendations](https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations)).
- **Reservations and savings plans.** A reservation commits to a specific resource product or configuration for a term and suits steady compute or database use; a savings plan commits to a fixed hourly spend across eligible services and regions and suits workloads that change ([Decide between a savings plan and a reservation](https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/decide-between-savings-plan-reservation)). Either is a commitment the client makes, not the framework.
- **Cache retirement** is a cost item too: Azure Cache for Redis tiers retire on fixed dates ([`services.md`](services.md)), and a migration left late is paid for twice.

## Where this stops

The budget amount, the alert recipients and the commitment purchases are the client's. Showback, chargeback and the FinOps practice of an organisation are not covered.
