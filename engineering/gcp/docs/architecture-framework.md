---
id: architecture-framework
type: doc
clade: engineering
subclade: gcp
title: The Google Cloud Well-Architected Framework, as This Plugin Uses It
summary: The six pillars and two perspectives of Google's Well-Architected Framework, the principles each pillar names, which artifact of this plugin or of the framework carries each into a design or a review, and what the enterprise foundations blueprint decides for an organization.
references:
  - docs/identity-and-access.md
  - docs/networking.md
  - docs/cost.md
  - docs/services.md
---

# The Google Cloud Well-Architected Framework, as This Plugin Uses It

Google's architecture guidance is published as the Well-Architected Framework (formerly the Google Cloud Architecture Framework), with six pillars and cross-pillar perspectives for AI and ML and for financial services ([Well-Architected Framework](https://docs.cloud.google.com/architecture/framework)). This document lists what each pillar asks and where that reaches a design or a review in this repository, so that `designing-on-gcp` and `reviewing-gcp` can walk the pillars without restating them. Pages were read on 2026-11-14; the principle names below are those on each pillar's landing page.

## The pillars

| Pillar | Principles the pillar page names | Where it lands here |
|---|---|---|
| [Security, privacy, and compliance](https://docs.cloud.google.com/architecture/framework/security) | security by design; zero trust; shift-left security; preemptive cyber defense; use AI securely and responsibly; use AI for security; meet regulatory, compliance and privacy needs | [`rules/identity-and-access.md`](../rules/identity-and-access.md), [`rules/data-protection.md`](../rules/data-protection.md), [`rules/exposure.md`](../rules/exposure.md), [`docs/networking.md`](networking.md); the security plugin's review disciplines for application code |
| [Reliability](https://docs.cloud.google.com/architecture/framework/reliability) | define reliability from user-experience goals; set realistic targets; redundancy for availability; horizontal scalability; detect failures with observability; graceful degradation; test recovery from failures; test recovery from data loss; postmortems | the region and zone choice of a design; `ahrena-engineering-reliability` for the code's behaviour under failure |
| [Operational excellence](https://docs.cloud.google.com/architecture/framework/operational-excellence) | operational readiness with CloudOps; manage incidents and problems; manage and optimize resources; automate and manage change; continuously improve | infrastructure as code (issue 295, `ahrena-engineering-terraform`), the delivery choices in [`docs/services.md`](services.md), `diagnosing-gcp-deployments` |
| [Cost optimization](https://docs.cloud.google.com/architecture/framework/cost-optimization) | align spending with business value; a culture of cost awareness; optimize resource usage; optimize continuously | [`rules/cost-attribution.md`](../rules/cost-attribution.md), [`docs/cost.md`](cost.md) |
| [Performance optimization](https://docs.cloud.google.com/architecture/framework/performance-optimization) | plan resource allocation; elasticity; modular design; monitor and improve continuously | the compute and data rows of [`docs/services.md`](services.md) |
| [Sustainability](https://docs.cloud.google.com/architecture/framework/sustainability) | low-carbon regions; energy-efficient AI and ML; resource usage; energy-efficient software; data and storage; measure and improve; culture; industry guidelines | the region choice of a design, recorded as a question for the owner when it trades against latency or residency |

The perspectives ([AI and ML](https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml), [financial services](https://docs.cloud.google.com/architecture/framework/perspectives/fsi)) apply the same pillars to those workloads; a design that is one of them reads its perspective as well.

A pillar is a lens for a design review, not a checklist that every change answers. A change that adds one Cloud Run service reads the security, reliability and cost pillars; a change to a dashboard reads none.

## What the enterprise foundations blueprint decides

Google's enterprise foundations blueprint (formerly the security foundations blueprint) is a Terraform-backed reference organization: defense in depth through policy, architecture and detective controls ([Enterprise foundations blueprint](https://docs.cloud.google.com/architecture/security-foundations)). What it decides is the vendor's own answer to the questions this plugin's rules ask, and what it decides for an organization is a reference, not a requirement on a client.

- **Hierarchy.** One organization, with folders for bootstrap, common, networking, and each environment ([Organization structure](https://docs.cloud.google.com/architecture/blueprints/security-foundations/organization-structure)). Google's landing-zone guidance says there is no single best hierarchy and advises against mirroring the organization chart ([Decide the resource hierarchy](https://docs.cloud.google.com/architecture/landing-zones/decide-resource-hierarchy)).
- **Identity.** Users and groups come from the existing identity provider through Cloud Identity, roles go to groups by job function, and changes go through a pipeline running as privileged service accounts ([Enterprise foundations blueprint](https://docs.cloud.google.com/architecture/security-foundations)).
- **Preventive controls.** Eighteen organization policy constraints enforced at the organization node, among them `iam.disableServiceAccountKeyCreation`, `iam.disableServiceAccountKeyUpload`, `iam.automaticIamGrantsForDefaultServiceAccounts`, `iam.allowedPolicyMemberDomains`, `storage.uniformBucketLevelAccess`, `storage.publicAccessPrevention`, `compute.skipDefaultNetworkCreation`, `compute.vmExternalIpAccess` and `sql.restrictPublicIp` ([Preventative controls](https://docs.cloud.google.com/architecture/blueprints/security-foundations/preventative-controls)).
- **Network.** Shared VPC per environment or hub-and-spoke, hierarchical firewall policies, Private Google Access, no direct internet in either direction, inbound through Cloud Load Balancing with Cloud Armor ([Networking](https://docs.cloud.google.com/architecture/blueprints/security-foundations/networking)).
- **Detective controls.** Organization-level log sinks to a central logging project, VPC Flow Logs on every subnet, Security Command Center ([Detective controls](https://docs.cloud.google.com/architecture/blueprints/security-foundations/detective-controls)).

Organizations created on or after 3 May 2024 already enforce a smaller baseline of seven constraints by default ([Manage baseline constraints](https://docs.cloud.google.com/resource-manager/docs/manage-baseline-constraints)); [`docs/identity-and-access.md`](identity-and-access.md) lists them.

## Where this stops

This document maps the framework; it does not reproduce its principles' content, which lives on the pages linked above and changes on Google's schedule. The blueprint's folder names, environments and network topology are its own and are not adopted by reference: each client's structure is recorded in its installation (`ahrena-engineering-fundamentals:rules/client-logic.md`).
