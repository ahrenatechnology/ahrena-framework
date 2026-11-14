---
id: services
type: doc
clade: engineering
subclade: cloud
title: Which Azure service, for which problem
summary: For each kind of problem a workload meets on Azure (compute, queueing, events, storage, relational, document and key-value data, caching, secrets and configuration, workload and customer identity, ingress, private access, egress, observability), the one service the framework recommends, why, and the case where it is the wrong choice.
references:
  - docs/architecture-framework.md
  - docs/networking.md
  - docs/identity-and-access.md
---

# Which Azure service, for which problem

The Azure counterpart of a language plugin's `libraries.md`. One recommendation per problem, the reason, and when not, each resting on the Microsoft page cited beside it. A recommendation is a starting point a design departs from with a written reason; it is not a ban on the alternatives. Pages read on 2026-11-14.

The Well-Architected item behind this page is PE:03 *Select the right services* ([Performance Efficiency checklist](https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/checklist)). Once a service is chosen, its [Well-Architected service guide](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/) is read before it is configured.

## Compute

**An HTTP service or a background worker, in a container: Azure Container Apps.** It runs general-purpose containers, especially applications made of many microservices, without the team operating Kubernetes. When not: it gives no direct access to the Kubernetes API, so a workload that needs the API or the control plane (operators, custom controllers, a Kubernetes-native toolchain) uses Azure Kubernetes Service ([Comparing Container Apps with other Azure container options](https://learn.microsoft.com/en-us/azure/container-apps/compare-options)). The compute decision guide describes Container Apps as the fit for teams that want modern patterns without Kubernetes complexity ([Choose an Azure compute service](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree)).

**Short, event-triggered code: Azure Functions.** Managed functions that run on triggers, for event-driven applications ([Choose an Azure compute service](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree)). When not: a long-running process or a service with its own HTTP server and lifecycle belongs in a container on Container Apps; Microsoft's comparison names Functions the ideal option for FaaS-style functions, not for general services ([compare-options](https://learn.microsoft.com/en-us/azure/container-apps/compare-options)).

**A web application that is not containerised: Azure App Service.** A managed host for web apps, mobile back ends and REST APIs; Microsoft calls it an ideal option for web apps ([compare-options](https://learn.microsoft.com/en-us/azure/container-apps/compare-options)). When not: a system of many services that scale and deploy separately is Container Apps' case.

**Full control of the operating system: Virtual Machines**, and only then. Infrastructure as a service gives the most control and portability and leaves provisioning, configuration and the network components to the team ([Choose an Azure compute service](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree)). When not: anything a managed host above can run, because every VM is an operating system someone patches.

## Messaging and events

**A work queue between services: Azure Service Bus.** Enterprise transactional messaging, with FIFO ordering through sessions, transactions, duplicate detection by message id and automatic dead-lettering ([Compare messaging services](https://learn.microsoft.com/en-us/azure/service-bus-messaging/compare-messaging-services); [Storage queues and Service Bus queues compared](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-azure-and-service-bus-queues-compared-contrasted)). When not: a queue that must hold more than 80 GB of messages, or a simple buffer that needs none of those guarantees, uses Azure Storage queues, which take up to 64 KB per message and are typically, not strictly, first in first out (same page).

**Reacting to something that happened: Azure Event Grid.** Reactive event routing, for status changes and serverless designs. When not: it gives no ordering guarantee, so a consumer that depends on order uses Service Bus sessions ([Compare messaging services](https://learn.microsoft.com/en-us/azure/service-bus-messaging/compare-messaging-services)).

**A stream of telemetry or data to be read in order and replayed: Azure Event Hubs.** Big-data streaming and ingestion, ordered per partition. When not: discrete business messages that each need one consumer, a transaction or a dead-letter queue are Service Bus' case (same page).

## Data

**Objects and files: Azure Blob Storage**, Microsoft's object storage for the cloud ([Introduction to Blob Storage](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction)). When not: data queried by its fields or joined to other data belongs in a database; Microsoft's data-model guide maps strict multi-entity transactions to relational stores and evolving aggregates to document stores ([Understand data models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models)).

**Relational data: Azure Database for PostgreSQL flexible server.** A fully managed PostgreSQL with granular control over configuration ([What is Azure Database for PostgreSQL?](https://learn.microsoft.com/en-us/azure/postgresql/overview)). The framework prefers it because the engine is the open-source one the team can run locally, in tests and on another cloud. When not: a workload already on SQL Server, or one that needs a SQL Server feature, uses Azure SQL Database, Microsoft's fully managed SQL Server engine as a service ([What is Azure SQL Database?](https://learn.microsoft.com/en-us/azure/azure-sql/database/sql-database-paas-overview)).

**Document data at global scale: Azure Cosmos DB**, a fully managed NoSQL and vector database. When not: Microsoft's own page names highly relational applications (use Azure SQL or MySQL) and analytical workloads (use Microsoft Fabric) as poor fits ([Azure Cosmos DB overview](https://learn.microsoft.com/en-us/azure/cosmos-db/overview)).

**A cache, or key-value lookups at very low latency: Azure Managed Redis**, an in-memory store based on Redis Enterprise ([What is Azure Managed Redis?](https://learn.microsoft.com/en-us/azure/redis/overview)). Not Azure Cache for Redis for anything new: its Enterprise and Enterprise Flash tiers retire on 31 March 2027, its Basic, Standard and Premium tiers on 30 September 2028, and Microsoft recommends upgrading to Azure Managed Redis now ([Azure Cache for Redis retirement FAQ](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/retirement-faq)). When not: the source of truth. A key-value store trades query expressiveness for latency ([Understand data models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models)), and a cache is rebuilt from somewhere else.

## Secrets and configuration

**Secrets, keys and certificates: Azure Key Vault**, one vault per application, region and environment, accessed with Azure RBAC ([Key Vault overview](https://learn.microsoft.com/en-us/azure/key-vault/general/overview); [Secure your Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault)). When not: settings that are not secret, and feature flags, go to Azure App Configuration, which Microsoft describes as complementing Key Vault ([What is Azure App Configuration?](https://learn.microsoft.com/en-us/azure/azure-app-configuration/overview)). Better still, a credential that a managed identity removes is not stored at all ([`identity-and-access.md`](identity-and-access.md)).

## Identity

**A workload's own identity: a managed identity**, user-assigned when several resources share it or when its role assignments must exist first; **a workload outside Azure: workload identity federation**. Why and when not: [`identity-and-access.md`](identity-and-access.md).

**Sign-in for a product's customers: Microsoft Entra External ID.** Azure AD B2C has not been available to new customers since 1 May 2025, and Microsoft calls it a legacy solution ([Microsoft Entra External ID overview](https://learn.microsoft.com/en-us/entra/external-id/external-identities-overview)). When not: an existing B2C tenant keeps working; moving it is a project of its own, not a side effect of another change.

## Network

**A public HTTP entry point serving more than one region: Azure Front Door**, global HTTP(S) load balancing with a web application firewall. When not: a regional application uses Application Gateway; non-HTTP traffic uses Azure Load Balancer ([Load balancing options](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/load-balancing-overview)).

**Private access to a PaaS service: a private endpoint**, with public network access disabled on the service. When not: service endpoints are the alternative, and Microsoft recommends Private Link over them; a service endpoint applies to every instance of the service ([Virtual network integration](https://learn.microsoft.com/en-us/azure/virtual-network/vnet-integration-for-azure-services)).

**Outbound internet from a subnet: a NAT gateway**, the method Microsoft recommends for most scenarios now that new virtual networks default to private subnets. When not: egress that must be filtered goes through Azure Firewall ([Default outbound access](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access)). Detail: [`networking.md`](networking.md).

## Observability

**Application telemetry: Application Insights through OpenTelemetry**, the Microsoft or Azure Monitor OpenTelemetry Distro for a new application; the classic Application Insights SDKs have an OpenTelemetry migration path, and OpenCensus for Python is retired ([Enable OpenTelemetry in Application Insights](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable); [Migrate to OpenTelemetry](https://learn.microsoft.com/en-us/azure/azure-monitor/app/migrate-to-opentelemetry)). The framework prefers instrumenting with OpenTelemetry because the instrumentation outlives the backend. When not: a project whose operations team already runs another OpenTelemetry backend exports there; the instrumentation does not change.

**The control-plane record: the Activity Log**, which records operations such as creating a resource or a deployment error and keeps them for 90 days; a diagnostic setting sends it to Log Analytics for longer ([Activity log](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/activity-log)). When not: it is not an authentication or authorization audit log, and a request Resource Manager rejects before an operation starts leaves no entry there (same page).

## Where this stops

Data analytics (Fabric, Synapse, Databricks), AI services, IoT and hybrid networking are not covered. Prices are not covered: they change, and a cost comparison belongs to the design that needs it, made with the [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/) on the day.
