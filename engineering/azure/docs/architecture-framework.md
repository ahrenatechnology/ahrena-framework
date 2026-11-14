---
id: architecture-framework
type: doc
clade: engineering
subclade: cloud
title: The Azure Well-Architected Framework and the Cloud Adoption Framework, as this plugin uses them
summary: The five Well-Architected pillars and their checklist codes, which a design and a review cite; the security pillar's encryption guidance behind the data-protection rule; where a workload sits in a Cloud Adoption Framework landing zone; and the governance tools (Azure Policy, Defender for Cloud, the Microsoft cloud security benchmark) that act as this plugin's detectors.
references:
  - rules/data-protection.md
  - rules/identity-and-access.md
  - rules/cost-attribution.md
  - docs/services.md
---

# The Azure Well-Architected Framework and the Cloud Adoption Framework

Microsoft publishes two frameworks that this plugin leans on, at two altitudes. The **Well-Architected Framework** is about one workload: its pillars say what a good design trades, and its checklists give each recommendation a code. The **Cloud Adoption Framework** is about the estate a workload lands in: management groups, subscriptions and landing zones. A design produced with this plugin cites the first by checklist code and takes the second as given by the client. Pages read on 2026-11-14.

## The five pillars

The framework's pillars, as its home page states their purpose ([Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/); [pillars](https://learn.microsoft.com/en-us/azure/well-architected/pillars)):

| Pillar | Purpose | Checklist |
|---|---|---|
| Reliability | meet uptime and recovery targets through redundancy and resiliency | RE:01 to RE:10 |
| Security | protect confidentiality and integrity against attack | SE:01 to SE:12 |
| Cost Optimization | keep spending within budget | CO:01 to CO:14 |
| Operational Excellence | reduce production issues through observability and automation | OE:01 to OE:11 |
| Performance Efficiency | adapt to demand through scaling and testing | PE:01 to PE:12 |

The checklists are the design review: [Reliability](https://learn.microsoft.com/en-us/azure/well-architected/reliability/checklist), [Security](https://learn.microsoft.com/en-us/azure/well-architected/security/checklist), [Cost Optimization](https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/checklist), [Operational Excellence](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/checklist), [Performance Efficiency](https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/checklist). Each item links to an architecture-strategies page. A design cites the code (`RE:04`, `SE:06`), so a reader can open the page the decision rests on.

The items a design touches most often:

- **RE:04 Define reliability and recovery targets.** No availability design is checkable without a target to check it against, and the target is the client's.
- **RE:05 Add redundancy at different levels.** On Azure that starts with availability zones: separated groups of datacenters within a region. A zone-redundant resource is replicated across zones by the service; a zonal one is placed in a zone the workload picks. Zones don't protect against a full-region outage ([What are availability zones?](https://learn.microsoft.com/en-us/azure/reliability/availability-zones-overview)).
- **SE:05 Strict, conditional, auditable IAM**, **SE:06 Isolate, filter, and control network traffic**, **SE:07 Encrypt data**, **SE:09 Protect application secrets.** These are [`identity-and-access.md`](identity-and-access.md), [`networking.md`](networking.md), the section below, and the secrets half of [`rules/identity-and-access.md`](../rules/identity-and-access.md).
- **OE:05 Standardized infrastructure as code** and **OE:11 Define safe deployment practices.** A change this plugin reviews is a template, and a deployment is previewed with what-if before it runs; the diagnosis skill starts from there.
- **OE:07 Design a monitoring stack.** Its guidance asks to scrub sensitive system or user information before logging while keeping enough context for diagnosis, and to keep workload data out of telemetry ([Designing a monitoring system](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/observability)). [`rules/exposure.md`](../rules/exposure.md) is that sentence made checkable.
- **PE:03 Select the right services.** [`services.md`](services.md).
- **CO:03 Collect and review cost data** and **CO:04 Set spending guardrails.** [`cost.md`](cost.md).

**Service guides** apply the pillars to one product: they highlight the features a well-architected design of that service needs. Guides exist for App Service, AKS, Cosmos DB, Azure Firewall, Blob Storage, Virtual Machines, Azure SQL Database, Application Gateway and others ([Azure service guides](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/)). A design that picks a service reads its guide before configuring it.

The **Azure Well-Architected Review** is Microsoft's questionnaire over the five pillars ([Azure Well-Architected Review](https://learn.microsoft.com/en-us/assessments/azure-architecture-review/)). It is the client's to run; a design produced here is the input it scores.

## Security pillar: encryption

The data-protection rule, [`rules/data-protection.md`](../rules/data-protection.md), rests on SE:07 ([Architecture strategies for encryption](https://learn.microsoft.com/en-us/azure/well-architected/security/encryption)): don't use TLS versions lower than 1.2; use HTTPS for all website communication regardless of the data's sensitivity; and encrypt persisted data with the native options of each storage service.

Most of that is already the platform's default, which is why the rule's conditions are about the settings a template can turn the wrong way:

- Azure encrypts data at rest by default with platform-managed keys; customer-managed keys add control at the cost of management responsibility ([Azure data encryption at rest](https://learn.microsoft.com/en-us/azure/security/fundamentals/encryption-atrest)).
- Azure Storage encryption is enabled for all accounts, uses 256-bit AES, and cannot be disabled ([Azure Storage encryption](https://learn.microsoft.com/en-us/azure/storage/common/storage-service-encryption)).
- Storage supports TLS 1.2 and 1.3. The portal sets the minimum to 1.2 for a new account; the CLI, PowerShell and templates leave `MinimumTlsVersion` unset, and an unset account permits TLS 1.0 or greater ([Enforce a minimum TLS version](https://learn.microsoft.com/en-us/azure/storage/common/transport-layer-security-configure-minimum-version)). This is the one default that is not the safe value, and the reason condition 1 asks for the property explicitly.
- Secure transfer required is enabled by default on a new storage account and rejects HTTP requests ([Require secure transfer](https://learn.microsoft.com/en-us/azure/storage/common/storage-require-secure-transfer)).
- Azure SQL Database enables TDE on every newly deployed database ([Transparent data encryption](https://learn.microsoft.com/en-us/azure/azure-sql/database/transparent-data-encryption-tde-overview)) and accepts nothing below TLS 1.2; TLS 1.0 and 1.1 are retired ([Connectivity settings](https://learn.microsoft.com/en-us/azure/azure-sql/database/connectivity-settings)).
- Azure Database for PostgreSQL flexible server always encrypts data at rest, with service-managed keys by default ([Data encryption at rest](https://learn.microsoft.com/en-us/azure/postgresql/security/security-data-encryption)).
- Key Vault soft delete is on by default and cannot be disabled once on, with a retention of 7 to 90 days set at creation; purge protection is optional and off by default ([Key Vault soft-delete](https://learn.microsoft.com/en-us/azure/key-vault/general/soft-delete-overview)).

The benchmark's data-protection controls are DP-3 *Encrypt sensitive data in transit*, DP-4 *Enable data at rest encryption by default*, DP-5 *Use customer-managed key option in data at rest encryption when required* and DP-6 *Use a secure key management process* ([MCSB: Data protection](https://learn.microsoft.com/en-us/security/benchmark/azure/mcsb-data-protection)). DP-5's "when required" is why condition 5 of the rule asks for a recorded requirement rather than a customer-managed key everywhere.

## Where a workload lands: the Cloud Adoption Framework

An Azure landing zone is Microsoft's architecture for governing, securing and scaling a multi-subscription environment. The *platform landing zone* is the shared foundation (governance, security, shared resources); a *workload landing zone* is where a workload team deploys within the platform's guardrails ([What is an Azure landing zone?](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/)).

Subscriptions are a unit of management, billing and scale ([Subscriptions design area](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/resource-org-subscriptions)). The management-group guidance keeps the hierarchy flat, ideally three or four levels, and says not to create management groups for production, test and development; where environments must be separated, separate them into different subscriptions in the same management group ([Management groups design area](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/resource-org-management-groups)).

For this plugin that means one thing: **the landing zone is input, not output.** A workload design names, for each environment, the subscription the client assigns to it (or records the question), and the platform services it attaches to; and the client's platform team decides the hierarchy, by [`client-logic.md`](../../fundamentals/rules/client-logic.md). A design that invents management groups for a client is designing the client's estate.

## The governance tools that act as detectors

The rules in this plugin name three kinds of detector that run in the client's tenant.

**Azure Policy** evaluates a resource when it is created or updated, and in a standard compliance cycle every 24 hours. Its effects include `deny`, `audit`, `modify`, `auditIfNotExists` and `deployIfNotExists`; Microsoft recommends starting with `audit` or `auditIfNotExists` before an enforcing effect ([Azure Policy overview](https://learn.microsoft.com/en-us/azure/governance/policy/overview); [effect basics](https://learn.microsoft.com/en-us/azure/governance/policy/concepts/effect-basics)). Each rule names the built-in definitions by display name, as the per-service policy references list them (for example [Storage](https://learn.microsoft.com/en-us/azure/storage/common/policy-reference), [Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/policy-reference), [Azure SQL](https://learn.microsoft.com/en-us/azure/azure-sql/database/policy-reference), [App Service](https://learn.microsoft.com/en-us/azure/app-service/policy-reference)).

**Microsoft Defender for Cloud** applies the Microsoft cloud security benchmark by default when it is turned on in a subscription, and only the benchmark's built-in recommendations affect the secure score ([Cloud secure score](https://learn.microsoft.com/en-us/azure/defender-for-cloud/secure-score-security-controls)). The benchmark's current version is v2, in preview, superseding v1 ([Microsoft cloud security benchmark overview](https://learn.microsoft.com/en-us/security/benchmark/azure/overview)); the control identifiers cited in this plugin (IM-3, PA-2, PA-4, PA-7, DP-3 to DP-6, NS-1 to NS-6) are read from the benchmark's control pages as published on the date above.

**Microsoft Entra access reviews**, covered in [`identity-and-access.md`](identity-and-access.md).

None of the three runs in this repository or in a pull request. A finding in a review is the reviewer's; the tenant's detectors are the backstop that catches what was deployed before the rule, or around it.

## Where this stops

This is not a summary of the Well-Architected Framework; it is the part a design or a review produced with this plugin cites. Workload-specific guidance (AI workloads, mission-critical, SAP) and the Cloud Adoption Framework's strategy, plan and migration methodologies are not covered.
