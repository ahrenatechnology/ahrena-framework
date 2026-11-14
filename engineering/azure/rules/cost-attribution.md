---
id: cost-attribution
type: rule
clade: engineering
subclade: cloud
title: Every Azure resource has an owner and a budget signal
statement: Every Azure resource carries an owner tag, and every subscription or resource group a workload runs in has a budget whose alert reaches a person.
enforcement: judgment
references:
  - docs/cost.md
---

# Every Azure resource has an owner and a budget signal

A resource nobody owns is a resource nobody turns off, and spend nobody is told about is noticed on the invoice. Three conditions. [`docs/cost.md`](../docs/cost.md) carries the reasons, the Cost Management behaviour that shapes them, and the Microsoft pages behind each.

## Conditions

1. **Every resource and resource group a change creates carries an owner tag.** The tag's name is the project's (the Cloud Adoption Framework's examples use `opsteam` and `businessunit` for ownership); its value names a team or a role that answers for the resource, never a person's personal data. Resources do not inherit their resource group's tags, so the tag is set on each resource, or an Azure Policy definition with the `modify` effect (*Inherit a tag from the resource group if missing*) copies it down. Decided in a change by a reviewer reading the template; in a running subscription by the built-in Azure Policy definitions *Require a tag on resources* and *Require a tag on resource groups* (effect `deny`).

2. **Every subscription or resource group a workload runs in has a Cost Management budget with at least one alert threshold whose recipient is a person or an action group that reaches one.** The state that fails is a workload scope with no budget, or a budget whose alerts go nowhere a person reads. Decided by a reviewer reading the budget's definition (in the template, or in Cost Management when it is not codified).

3. **An environment that is not production says when it stops.** A development, test or preview environment carries the date or the event after which it is deleted, as a tag or in the design record, and a resource created for an experiment is created in a resource group that is deleted with it. Decided by a reviewer.

## Where this stops

**Budgets do not stop anything.** A Cost Management budget notifies; it does not stop resources or consumption. Capping spend is a design decision (a scale limit, a quota, an automation an action group runs), recorded in the design, and this rule does not require one.

**The amount is the client's.** What the budget is, and who receives its alerts, belongs to the installation by [`client-logic.md`](../../fundamentals/rules/client-logic.md). The rule checks that a budget exists and reaches someone; it never names a figure.

**Tag inheritance in Cost Management is not condition 1.** It copies subscription and resource group tags onto usage records, which is enough for a cost report and not enough for the person who opens the resource and asks whose it is.

**Rightsizing, reservations and savings plans are not conditions.** They are optimisations [`docs/cost.md`](../docs/cost.md) discusses; a workload that pays list price for the right resources has broken nothing here.
