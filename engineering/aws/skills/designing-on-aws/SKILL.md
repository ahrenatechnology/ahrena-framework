---
name: designing-on-aws
description: Use when a feature, service or workload needs AWS infrastructure and nothing is built yet - a new service, a new data store, a queue between two services, a redesign for cost or availability. Turns requirements into a written design - one service per problem from the recommended list, the identity and network it needs, encryption, the owner tag and budget, a pass over the six Well-Architected pillars - with every departure from a recommendation argued. It designs; it writes no infrastructure code.
type: skill
clade: engineering
subclade: aws
references:
  - rules/least-privilege.md
  - rules/data-protection.md
  - rules/exposure.md
  - rules/cost-ownership.md
  - docs/services.md
  - docs/well-architected.md
  - docs/identity-and-access.md
  - docs/networking.md
  - docs/cost.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-contributing:skills/writing-decision-records/SKILL.md
---

# Designing on AWS

The output is one design document, written from `references/design-template.md`, that a builder can implement and a reviewer can hold the result to. Every choice in it names its reason; every reason that is a fact about AWS names its page.

## 1. Settle the requirements, or stop

Read the issue and the project's component map with `ahrena-engineering-fundamentals:reading-the-component-map`: the vocabulary, what already runs on AWS, the deployment tool, the owner tag key, the environments.

Then establish, from the issue or by asking: what the workload does on its main paths; the load it must carry and its shape (steady, spiky, idle most of the day); the latency it must meet; what an outage costs and how much data loss is tolerable; what data it holds and whether any of it is personal, payment or regulated; where that data may live; and the budget it must fit. A design built on a guessed number is a guess, so a missing one that changes the design is a question back to the issue's owner, asked in one batch, before step 2.

The recurring failure here is designing for a load nobody stated. Write "not stated" next to any figure the issue did not give and the design assumed.

## 2. Map the flows

List the components, the data each holds and how it is read (by key, by query, by scan), and every path a request or an event takes between them, synchronous or not. Draw it in the template's diagram block. A flow with no owner component, or data with no owning store, is the design's first defect.

## 3. Choose one service per problem

For each component, take the recommendation for its kind of problem from `docs/services.md` and check its "when not" against step 1's numbers: a handler that runs longer than Lambda's limit, a message order the standard queue does not keep, an item larger than DynamoDB's, an engine Aurora does not offer. Keep what the project already runs unless the design has a reason to change it.

Write each choice with its reason and the alternative considered. A departure from `docs/services.md` is a decision: record it with `ahrena-contributing:writing-decision-records` when it affects more than one component or will be questioned later.

## 4. Design identity

Per component, the role it runs under and the actions on the resources it calls, from the flows in step 2 — never a wildcard to save time (`rules/least-privilege.md`). People reach the accounts through federation; a third party gets a role with an external ID. Read `docs/identity-and-access.md` for the evaluation logic when a boundary or a guardrail is involved.

## 5. Design the network

Private subnets for compute and data; public only for what the internet must reach; security groups that reference each other; gateway endpoints for S3 and DynamoDB; Session Manager instead of an inbound administrative port; one NAT gateway per zone in production. `docs/networking.md` argues each default and the trade a non-production environment may make.

## 6. Protect the data

Encryption at rest for every store, created that way; TLS on every client-facing listener with its policy named; credentials in Secrets Manager; a customer managed key only where the design says who alone may read the data (`rules/data-protection.md`).

Then the exposure boundary: name the layer that calls AWS in each component, and state what it returns to its caller when an AWS call fails — a generic error and a correlation ID — and what it logs, as named fields (`rules/exposure.md`). This sentence goes in the design so the builder writes it from the first line.

## 7. Cost it

Every resource carries the owner tag; the account has a budget with a forecast alert (`rules/cost-ownership.md`). Estimate the monthly cost of the design for its Region and stated load with the AWS Pricing Calculator, record the date of the estimate and the assumptions behind it, and compare it with the budget from step 1. `docs/cost.md` lists the defaults that cost money silently — log retention, NAT for AWS-service traffic — and the design states its value for each.

## 8. Walk the pillars

One sentence per pillar of `docs/well-architected.md` — operational excellence, security, reliability, performance efficiency, cost optimization, sustainability — naming the decision the design made and the trade-off it accepted. A pillar where nothing applies says so and why. This is the check that nothing was skipped, not a second design.

## 9. Write the document

Fill `references/design-template.md` and put it where the project keeps designs, or in the issue if it keeps none. Nothing in it names a client, a real account ID, an ARN or an address: placeholders and the project's own component names only.

## When this skill does not apply

**Infrastructure code.** Writing the CloudFormation, CDK or Terraform is the builder's, against this design; Terraform as a language is the infrastructure-as-code plugin's.

**A review of something already designed or built.** That is `skills/reviewing-aws/SKILL.md` for a change, or the Well-Architected Tool for a running workload.

**A failing deployment.** That is `skills/diagnosing-aws-deployments/SKILL.md`.

**A client's account structure.** Which accounts, organizational units and guardrails a client runs is client logic; the design reads it as a given.
