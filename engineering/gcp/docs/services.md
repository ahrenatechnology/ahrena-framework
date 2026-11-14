---
id: services
type: doc
clade: engineering
subclade: gcp
title: Which Google Cloud Service for Which Problem
summary: For each kind of problem a product on Google Cloud meets (compute, scheduling and messaging, object storage, relational, document and key-value data, analytics, secrets, identity, networking, observability, delivery), the service this framework starts from, the reason, and the case where it is the wrong choice.
references:
  - docs/architecture-framework.md
  - docs/identity-and-access.md
  - docs/networking.md
  - docs/cost.md
---

# Which Google Cloud Service for Which Problem

This is the Google Cloud counterpart of a language plugin's `libraries.md`: one starting recommendation per problem, the reason, and when it is wrong. A recommendation is where the design starts, not where it must end; the "when not" column is what a design reads before it departs, and a departure names which case it is.

Two premises decide between options when the vendor's own pages leave the choice open, and a row whose choice the vendor's page does not make names the premise it uses:

- **Least operation.** The managed or serverless service is preferred over one the team runs, because what the team does not run it cannot misconfigure, patch late or leave unmonitored. Google's own guide makes the same call for containers: consider serverless first, unless the workload needs Kubernetes ([Select a managed container runtime](https://docs.cloud.google.com/architecture/select-managed-container-runtime-environment)).
- **The smallest service that meets the requirement.** A service sized for a requirement the product does not have is cost and operation paid for nothing.

Every vendor statement below was read on 2026-11-14 under `docs.cloud.google.com`. Where a "when not" is this framework's inference rather than the vendor's sentence, the row says so.

## Compute

| Problem | Start with | Why | When not |
|---|---|---|---|
| An HTTP service, an API, a web application, a push handler for Pub/Sub or Eventarc | **Cloud Run service** | It runs a container that answers HTTP on a stable endpoint with no server or cluster to manage, and scales to zero ([What is Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run); [Choose a compute option](https://docs.cloud.google.com/docs/compute-area/choose-compute-options)). Least operation. | The workload needs the Kubernetes API, custom resources or Helm, persistent volumes, Arm, Kubernetes RBAC for multi-tenancy, or tasks longer than Cloud Run's maximum timeout (60 minutes for a request, [Request timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout)): use GKE Autopilot ([Select a managed container runtime](https://docs.cloud.google.com/architecture/select-managed-container-runtime-environment)). |
| A task that runs to completion: a migration, a batch, a scheduled job | **Cloud Run job** | Runs to completion, manually or on a schedule, without serving requests ([What is Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run)). | Large scheduled batch with queuing across many machines: Batch ([Choose a compute option](https://docs.cloud.google.com/docs/compute-area/choose-compute-options)). |
| An always-on consumer that pulls from a queue | **Cloud Run worker pool** | Built for pull consumers of Pub/Sub, Kafka or RabbitMQ, with no endpoint ([What is Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run)). | The consumer must scale on load on its own: the page says worker pools do not autoscale natively, so use a push subscription to a Cloud Run service instead. |
| A single function triggered by an event | **Cloud Run functions** | Functions are now deployed as Cloud Run services and priced as Cloud Run ([Cloud Run functions comparison](https://docs.cloud.google.com/run/docs/functions/comparison)). | More than one entry point or a container you build yourself: a Cloud Run service (this framework's inference, by least operation). |
| Containers that need Kubernetes | **GKE Autopilot** | Google names Autopilot the default and recommended mode and says to use it for most workloads ([Choose a cluster mode](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/choose-cluster-mode)). | Workloads that need node-level control or special privileges: GKE Standard (same page). |
| A custom kernel, OS or architecture | **Compute Engine** | For configurations and kernel settings a managed runtime does not allow ([Choose a compute option](https://docs.cloud.google.com/docs/compute-area/choose-compute-options)). | Anything a container can carry: orchestration and patching on VMs are the team's, which is the cost least operation avoids. |
| An existing App Engine application | keep it running, plan the move | App Engine is not retired as a whole, but its first-generation runtimes were deprecated on 2026-01-31 and Google suggests considering Cloud Run ([App Engine long-term support](https://docs.cloud.google.com/appengine/docs/standard/long-term-support)). | A new application: start on Cloud Run. |

## Scheduling, messaging and orchestration

| Problem | Start with | Why | When not |
|---|---|---|---|
| Fan an event out to any number of consumers that the publisher does not know | **Pub/Sub** | It decouples publishers from subscribers, supports several subscriptions per message, pull delivery and ordering keys ([Choose Pub/Sub or Cloud Tasks](https://docs.cloud.google.com/pubsub/docs/choosing-pubsub-or-cloud-tasks)). | Synchronous request and reply with a mobile or web client, or an existing Kafka estate: Pub/Sub's overview points elsewhere for both ([Pub/Sub overview](https://docs.cloud.google.com/pubsub/docs/overview)). |
| Hand one specific call to one handler, later, with a rate limit or a set number of retries | **Cloud Tasks** | The publisher keeps control of execution: scheduled delivery, rate limits, retry limits, deduplication at creation ([Choose Pub/Sub or Cloud Tasks](https://docs.cloud.google.com/pubsub/docs/choosing-pubsub-or-cloud-tasks)). | More than one consumer for the same message: Pub/Sub. |
| Run something on a cron schedule | **Cloud Scheduler** | Cron jobs to HTTP, Pub/Sub or App Engine targets ([Cloud Scheduler overview](https://docs.cloud.google.com/scheduler/docs/overview)). | Delivery is at least once, and the page asks for idempotent targets; a target that is not idempotent is the defect, not the scheduler. |
| React to something that happened in a Google service or a SaaS | **Eventarc** | Routes events from Google services, applications and SaaS to destinations ([Eventarc overview](https://docs.cloud.google.com/eventarc/docs/overview)). | An event the application itself publishes to its own consumers: Pub/Sub directly (this framework's inference, by the smallest service). |
| Coordinate several steps with state, retries and waits | **Workflows** | Serverless orchestration of Cloud Run, functions and APIs with state and retries ([Workflows overview](https://docs.cloud.google.com/workflows/docs/overview)). | Work that is computation rather than coordination: the page itself says to put work too complex for Workflows in a service. |

## Object storage

| Problem | Start with | Why | When not |
|---|---|---|---|
| Files, uploads, artefacts, backups | **Cloud Storage, Standard class**, with uniform bucket-level access | No minimum storage duration; uniform access makes IAM the only path ([Storage classes](https://docs.cloud.google.com/storage/docs/storage-classes); [Uniform bucket-level access](https://docs.cloud.google.com/storage/docs/uniform-bucket-level-access)). | Data read about once a month or less: Nearline (30-day minimum); once a quarter: Coldline (90 days); retention and disaster recovery: Archive (365 days) ([Storage classes](https://docs.cloud.google.com/storage/docs/storage-classes)). A class with a minimum duration costs more than Standard for data deleted sooner. |

## Data

Google publishes no single "choose a database" decision page; the product list groups the options without selection criteria ([Databases](https://docs.cloud.google.com/docs/databases)). The rows below are therefore this framework's choice, argued from the smallest service that meets the requirement and from each product's own page.

| Problem | Start with | Why | When not |
|---|---|---|---|
| A relational database for one application | **Cloud SQL for PostgreSQL** | A fully managed relational service; Google's page says to use it to spend less time managing the database ([Cloud SQL introduction](https://docs.cloud.google.com/sql/docs/introduction)). | The page notes some configuration changes and maintenance cause downtime; a workload that cannot take that, or that mixes transactions with analytics, reads AlloyDB. |
| PostgreSQL under demanding load: transactions with analytics on the same data, low-latency AI, mission-critical | **AlloyDB for PostgreSQL** | Google designs it for those workloads, with a columnar engine and compute separate from storage ([AlloyDB overview](https://docs.cloud.google.com/alloydb/docs/overview)). | An ordinary application database: Cloud SQL is the smaller service (this framework's inference; the AlloyDB page draws no comparison). |
| Relational data that must be strongly consistent across regions | **Spanner** | ACID with external consistency and synchronous replication; multi-region configurations, with up to 99.999% availability in Enterprise Plus ([Replication](https://docs.cloud.google.com/spanner/docs/replication); [TrueTime and external consistency](https://docs.cloud.google.com/spanner/docs/true-time-external-consistency); [Editions](https://docs.cloud.google.com/spanner/docs/editions-overview)). | One region and one application's load: the smallest instance is 100 processing units, and multi-region needs Enterprise Plus ([Editions](https://docs.cloud.google.com/spanner/docs/editions-overview)); Cloud SQL is the smaller service (this framework's inference). |
| Documents read and written by a mobile or web application, with no capacity to provision | **Firestore** | A fully managed document database, pay per use, no pre-provisioning, scales with load, optionally integrated with Firebase ([Firestore overview](https://docs.cloud.google.com/firestore/native/docs/overview)). | Relational structure with joins, or interactive analytics: Cloud SQL or BigQuery (this framework's inference from the data model). |
| High-throughput, low-latency key-value or time series at large scale | **Bigtable** | Built for that, with values typically up to 10 MB ([Bigtable overview](https://docs.cloud.google.com/bigtable/docs/overview)). | The page says it is not a traditional relational database; structured documents needing ACID go to Firestore, interactive analytics to BigQuery. |
| A cache or session store | **Memorystore for Redis** (or for Valkey) | Managed in-memory store ([Memorystore for Redis](https://docs.cloud.google.com/memorystore/docs/redis/memorystore-for-redis-overview)). | Memorystore for Memcached is marked deprecated in the product list ([Databases](https://docs.cloud.google.com/docs/databases)). |
| Analytics over large data | **BigQuery** | A serverless data platform with columnar storage built for analytical queries ([BigQuery introduction](https://docs.cloud.google.com/bigquery/docs/introduction)). | Serving an application's transactions: an operational database above. |

## Secrets and configuration

| Problem | Start with | Why | When not |
|---|---|---|---|
| An API key, password or certificate | **Secret Manager** | Versioned secrets with IAM per secret ([Secret Manager overview](https://docs.cloud.google.com/secret-manager/docs/overview)). | Configuration that is not secret (connection strings without credentials, feature flags): Parameter Manager; cryptographic operations with a key: Cloud KMS (same page). |

## Identity

| Problem | Start with | Why | When not |
|---|---|---|---|
| A workload on Google Cloud calling Google APIs | **the attached service account** | No key to leak ([Best practices for using service accounts](https://docs.cloud.google.com/iam/docs/best-practices-service-accounts)). | On GKE: Workload Identity Federation for GKE. |
| A workload outside Google Cloud (CI, another cloud) calling Google APIs | **Workload Identity Federation** | Removes the maintenance and security burden of service account keys ([Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation)). | The external platform issues no OIDC or SAML token: then, and only then, a key, under condition 4 of [`rules/identity-and-access.md`](../rules/identity-and-access.md). |
| The workforce's users and groups | **Cloud Identity**, federated with the existing provider | Central management of users and groups that IAM then grants to ([Cloud Identity overview](https://docs.cloud.google.com/identity/docs/overview)). | An application's own customers: Identity Platform. |
| An application's own end users | **Identity Platform** | The backend of Firebase Authentication, with MFA, OIDC and SAML, and multi-tenancy ([Identity Platform comparison](https://docs.cloud.google.com/identity-platform/docs/product-comparison)). | Employees of the organization: Cloud Identity. |

## Networking

| Problem | Start with | Why | When not |
|---|---|---|---|
| Serve HTTP from the internet | **external Application Load Balancer with Cloud Armor**, Cloud Run ingress `internal-and-cloud-load-balancing` | Layer 7 proxy with WAF and DDoS protection in front of a serverless backend, which the internet cannot reach directly ([External Application Load Balancer](https://docs.cloud.google.com/load-balancing/docs/https); [Cloud Armor](https://docs.cloud.google.com/armor/docs/cloud-armor-overview); [Cloud Run ingress](https://docs.cloud.google.com/run/docs/securing/ingress)). | An internal service: ingress `internal`. |
| Outbound internet from private workloads | **Cloud NAT** | No inbound connections, no proxy VMs ([Cloud NAT](https://docs.cloud.google.com/nat/docs/overview)). | Traffic to Google APIs: Private Google Access, not NAT. |
| Cloud Run reaching a VPC | **Direct VPC egress** | The page labels it recommended; connectors cost more to maintain and run ([Connecting to a VPC](https://docs.cloud.google.com/run/docs/configuring/connecting-vpc)). | A subnet without room for the addresses Direct VPC egress takes: a Serverless VPC Access connector. |
| Administrative access to a VM | **IAP TCP forwarding** | SSH or RDP without a public port ([IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding)). | A VM that must accept SSH from a system that cannot run the gcloud client or reach IAP: that system then needs its own reviewed firewall rule, and the exception is recorded in the change (this framework's inference). |

[`docs/networking.md`](networking.md) argues the network as a whole.

## Observability

| Problem | Start with | Why | When not |
|---|---|---|---|
| Instrumentation | **OpenTelemetry** exporting to Google Cloud | Google recommends vendor-neutral open-source instrumentation ([Instrumentation overview](https://docs.cloud.google.com/stackdriver/docs/instrumentation/overview)). | A service so small that the platform's built-in request metrics and logs answer every question asked of it: instrumenting it is cost with no reader (this framework's inference, by the smallest service). |
| Logs | **Cloud Logging** | Real-time log management with storage, search and analysis ([Cloud Logging overview](https://docs.cloud.google.com/logging/docs/overview)). | Logs another system must own, for retention or a SIEM: keep Cloud Logging as the source and route copies with a sink ([Routing overview](https://docs.cloud.google.com/logging/docs/routing/overview)), rather than writing to the other system from the application. |
| Metrics and alerts | **Cloud Monitoring**; **Managed Service for Prometheus** where the team already writes PromQL | Monitoring owns metrics and alerting; the Prometheus service is fully managed, cross-project, with managed collection recommended ([Observability overview](https://docs.cloud.google.com/stackdriver/docs); [Managed Service for Prometheus](https://docs.cloud.google.com/stackdriver/docs/managed-prometheus)). | Metrics the team already collects with another vendor's agent and dashboards, where moving them buys nothing the product needs: keep them there and export Google Cloud's metrics to it (this framework's inference, by least operation). |
| Errors grouped by cause | **Error Reporting** | Groups errors it finds in Cloud Logging ([Grouping errors](https://docs.cloud.google.com/error-reporting/docs/grouping-errors)). | It reads logs, so an error that is not logged is not reported. |

## Delivery

| Problem | Start with | Why | When not |
|---|---|---|---|
| Container images and packages | **Artifact Registry** | The recommended registry; Container Registry was shut down for writes on 2025-03-18 ([Transition from Container Registry](https://docs.cloud.google.com/artifact-registry/docs/transition/transition-from-gcr)). | Images that must also be pulled by platforms outside Google Cloud under the team's existing registry: keep that registry as the source and mirror into Artifact Registry for Google Cloud's runtimes (this framework's inference). |
| Infrastructure as code | **Terraform**, run by **Infrastructure Manager** or the team's pipeline | Infrastructure Manager runs Terraform in Cloud Build and manages its state ([Infrastructure Manager overview](https://docs.cloud.google.com/infrastructure-manager/docs/overview)). | Not Deployment Manager: its support ended in 2026 and it is turned down after 2027-06-30 ([Deployment Manager deprecations](https://docs.cloud.google.com/deployment-manager/docs/deprecations)). A platform run entirely through Kubernetes may use Config Connector ([Config Connector](https://docs.cloud.google.com/config-connector/docs/overview)). Terraform as a language is `ahrena-engineering-terraform`'s (issue 295). |

## Where this stops

A recommendation here does not override a decision a client has already recorded in its installation; client structure is not platform content (`ahrena-engineering-fundamentals:rules/client-logic.md`). Prices are not given, because they change and Google's pricing pages are the source; [`docs/cost.md`](cost.md) covers how cost is attributed and bounded. AI and ML services are outside this table.
