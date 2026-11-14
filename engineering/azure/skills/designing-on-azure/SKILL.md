---
name: designing-on-azure
description: Use when a workload, or a change to one, is being designed to run on Azure - choosing the services, the identities and role assignments, the network reach, the data protection, how errors leave the application and how cost is attributed - before any template or code is written. Produces a design record that cites, for each decision, the Well-Architected checklist code and this plugin's rule or doc behind it.
type: skill
clade: engineering
subclade: cloud
references:
  - rules/identity-and-access.md
  - rules/data-protection.md
  - rules/exposure.md
  - rules/cost-attribution.md
  - docs/services.md
  - docs/architecture-framework.md
  - docs/identity-and-access.md
  - docs/networking.md
  - docs/cost.md
---

# Designing on Azure

The output is a design record, a markdown file in the repository (where the project keeps its decision records, or beside the infrastructure code), with one section per step below. Each decision names the Well-Architected checklist code it serves and the rule or doc of this plugin it applies, so a reviewer can check it against the page.

## 1. Take the client's estate as input

Read what the client has already decided: the tenant, the landing zone, the subscriptions per environment, the hub the workload attaches to, the Azure Policy assignments and whether Defender for Cloud is on. Read `docs/architecture-framework.md`, section *Where a workload lands*.

The recurring failure here is designing the estate: inventing management groups, a hub or a naming scheme for a client that has one. Those are the client's, by `ahrena-engineering-fundamentals:rules/client-logic.md`. Where the estate is unknown, write the question in the record and continue with the workload; do not fill the gap with a guess. Never copy a real subscription id, tenant id or principal id into the record: name the subscription by its role (`production`, `staging`) only.

## 2. Write the targets

Before choosing anything, write the targets the design is checked against: availability and recovery (RE:04), the performance targets of the critical flows (PE:01), the data's classification and any requirement for a customer-managed key (SE:03, DP-5), and the spending envelope (CO:02). A target the client has not given is a question in the record, not a number the designer invents.

## 3. Choose the services

For each problem the workload has, take the recommendation in `docs/services.md` and write the reason it fits, or the reason the design departs from it, citing the page. Then open the service's Well-Architected service guide, if it has one, by its URL with a fetch tool, and note the configuration it calls for. A page that cannot be opened is recorded as not read, with its URL, as an open question; it is never filled in from memory.

Two failures recur. Choosing by familiarity (AKS because the team knows Kubernetes, when nothing needs the Kubernetes API) is a departure without a reason. And choosing a service that is retiring (Azure Cache for Redis, Azure AD B2C for a new tenant) buys a migration on day one.

## 4. Design the identities

For each component, write: the identity it runs as (a managed identity, user-assigned when it is shared or must exist first, or a federated credential for code outside Azure), every Azure resource it calls, and the role and scope each call needs. Apply `rules/identity-and-access.md` conditions 1 to 3; `docs/identity-and-access.md` has the reasons.

The table this step produces is the one the review checks. A component whose role column says `Contributor` has not been designed yet. For the deployment pipeline, write its federated credential and its role the same way: a pipeline is a workload with the widest reach in the system.

## 5. Design the network reach

For each service, write whether it is public and why, and if not, how it is reached: a private endpoint, its private DNS zone, and public network access disabled. Write the entry point for public traffic and its WAF, and the egress method. Apply `rules/identity-and-access.md` condition 4 with `docs/networking.md`.

## 6. Design data protection

For each data store, write its minimum TLS setting, whether HTTP is refused, whether encryption at rest is default or customer-managed and why, and for Key Vault whether purge protection is on. Apply `rules/data-protection.md`; the defaults that are not safe are listed in `docs/architecture-framework.md`, section *Security pillar: encryption*.

## 7. Design the error boundary

Write where an Azure SDK error is caught and translated before it reaches a caller, what the caller receives (a generic message, a status, a correlation id), and which named fields the internal log records (operation, status, Azure error code, correlation id). Apply `rules/exposure.md` conditions 1 and 2. Write which tags and outputs the templates will carry, checked against condition 3.

This step is the one most designs skip, because nothing fails when it is skipped until a client reads the error. Write it even for a workload with one endpoint.

## 8. Design cost attribution

Write the owner tag's name and how it reaches every resource (set per resource, or an Azure Policy `modify` assignment), the budget scope and who its alerts reach, and for each non-production environment when it ends. Apply `rules/cost-attribution.md` with `docs/cost.md`.

## 9. Check the record against the checklists

Walk the five Well-Architected checklists in `docs/architecture-framework.md` and mark each item the design addresses, the ones it leaves to the client, and the ones it does not address with the reason. Then list the questions from steps 1 and 2 that are still open. The design is done when every rule condition of this plugin has a line in the record that satisfies it or a recorded reason it does not apply.

## When this skill does not apply

**Reviewing a design or a change that already exists.** That is `reviewing-azure`.

**A deployment that failed.** That is `diagnosing-azure-deployments`.

**Writing the templates.** This skill decides what the infrastructure is; writing the Bicep or Terraform that builds it is the infrastructure-as-code language's work (the Terraform plugin, issue #295), checked afterwards by `reviewing-azure`.

**Designing the client's estate.** Landing zones, management groups and the hub are the client's platform team's, not a workload design's.
