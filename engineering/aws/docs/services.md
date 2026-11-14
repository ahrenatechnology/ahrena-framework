---
id: services
type: doc
clade: engineering
subclade: aws
title: Which AWS Service for Which Problem
summary: For each kind of problem a workload on AWS has — compute, queueing and events, storage, relational and key-value data, secrets and configuration, identity, networking and edge, observability — the one service this framework recommends, the reason grounded in AWS's own decision guides and service pages, and the case where it is the wrong choice.
references:
  - docs/well-architected.md
  - docs/identity-and-access.md
  - docs/networking.md
  - docs/cost.md
  - rules/data-protection.md
---

# Which AWS Service for Which Problem

This is the AWS counterpart of a language plugin's `libraries.md`: for each kind of problem, one recommendation, why, and when not. A designer starts from the recommendation and departs from it only for a reason this page or the project states. Every claim cites the AWS page it was read from on 2026-11-14 — mostly the [AWS Decision Guides](https://docs.aws.amazon.com/decision-guides/), which are AWS's own statement of how to choose.

## The premises that decide

When AWS's guides leave a choice open, three premises close it, in this order.

1. **The fewest components the workload operates.** The Well-Architected framework lists "Use managed services" under two pillars and "Stop spending money on undifferentiated heavy lifting" under a third ([`docs/well-architected.md`](well-architected.md)). A managed service the workload does not patch, scale or fail over is one less thing a small team carries.
2. **A known failure mode over a better benchmark.** A service whose limits are published (a timeout, a payload size, a throughput ceiling) is preferred to one chosen for a performance figure, because the limit is what the design is checked against. Where two AWS pages disagree on a figure, this page cites neither (see relational data).
3. **No second service for a problem one already solves.** A workload that already runs containers on ECS does not add Lambda for a long-running handler, and the other way round.

## Compute

| | |
|---|---|
| **Recommended** | **AWS Lambda** for event-driven handlers and short request work; **Amazon ECS on AWS Fargate** for a long-running service or a container image. |
| **Why** | The compute guide frames Lambda as running "code without provisioning or managing servers" ([Choosing an AWS compute service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-compute-service.html)). The container guide calls ECS "an AWS-native orchestrator with lower operational overhead" and Fargate a "serverless compute engine with which you can run containers" ([Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-container-service.html)). Neither has a server or a control plane for the workload to run. |
| **When not** | Lambda: a function runs at most "900 seconds (15 minutes)", a synchronous request and response are each at most 6 MB, and memory tops out at 10,240 MB ([Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)) — work that exceeds any of these is not Lambda's. Fargate: no GPU, and ECS tasks on Fargate must fit "within 32 vCPU and 244 GiB (Linux)" (container guide). Choose **Amazon EKS** when the team needs "the Kubernetes API and ecosystem, portability across clouds and on-premises" (container guide); for EKS the guide recommends EKS Auto Mode over Fargate. Choose **EC2** directly only when the workload needs control of the instance the others do not give. |

## Queueing, fan-out and events

| | |
|---|---|
| **Recommended** | **Amazon SQS standard queue** to hand work from a producer to a consumer. **Amazon SNS** to fan one message out to several subscribers. **Amazon EventBridge** to route events between services by rule. |
| **Why** | SQS is "fully managed message queuing service that enables decoupling and scaling of microservices", pull-based and at-least-once, with retention up to 14 days; SNS is a "fully managed publish-subscribe (pub/sub) messaging model", push-based; EventBridge is a "fully managed event bus service for event-driven architectures" that matches events to targets by rule ([Amazon SQS, Amazon SNS, or Amazon EventBridge?](https://docs.aws.amazon.com/decision-guides/latest/sns-or-sqs-or-eventbridge/sns-or-sqs-or-eventbridge.html)). A standard queue offers "Guaranteed at-least-once delivery" and "best-effort ordering" with a "nearly unlimited number of API calls per second" ([Amazon SQS queue types](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-types.html)). |
| **When not** | Use an **SQS FIFO** queue when order matters — it delivers "in the order they are sent within each message group" with "exactly-once processing" — and accept its ceiling: up to 300 API calls per second per method, 3,000 messages per second with batching, up to 30,000 TPS in high-throughput mode (queue types page). Do not use EventBridge as a queue: the decision guide says it does not persist events and gives no ordering guarantee. Do not use SNS alone where a subscriber must not lose a message while it is down; put a queue behind it. A standard queue delivers at least once, so its consumer is idempotent; that is `ahrena-engineering-reliability:reviewing-reliability`. |

## Storage

| | |
|---|---|
| **Recommended** | **Amazon S3** for objects: files, uploads, exports, static assets, backups. |
| **Why** | The storage guide gives S3 for "read-heavy workloads such as content distribution, web hosting, big data analytics, and ML workflows" ([Choosing an AWS storage service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-storage-service.html)). Every new object is encrypted by default since January 5, 2023, and new buckets do not allow public access by default ([Default encryption FAQ](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-encryption-faq.html), [Blocking public access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)), so the safe state is the one it starts in. |
| **When not** | A file system a process mounts: **Amazon EBS** for "low-latency, high-performance durable storage attached to single Amazon EC2 instances or containers, such as databases", **Amazon EFS** for "shared read and write access across multiple Amazon EC2 instances or containers" (storage guide). For data whose access pattern is unknown, S3 stays the service and Intelligent-Tiering the storage class ([`docs/cost.md`](cost.md)). |

## Relational data

| | |
|---|---|
| **Recommended** | **Amazon Aurora PostgreSQL-Compatible Edition.** |
| **Why** | Aurora "is part of the managed database service Amazon Relational Database Service", with a cluster volume that grows to 256 TiB ([What is Amazon Aurora?](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html)). The database guide recommends it for "migrating or modernizing an on-premises relational workload, or if your workload has less predictable query patterns" ([Choosing an AWS database service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/databases-on-aws-how-to-choose.html)). Between its two engines the AWS pages read here argue no preference; the framework names PostgreSQL so that the default is one engine and not a menu, and a project that already runs MySQL keeps it (premise 3). |
| **When not** | An engine Aurora does not offer: Aurora is MySQL- and PostgreSQL-compatible only, while **Amazon RDS** offers PostgreSQL, MySQL, MariaDB, SQL Server, Oracle and Db2 (database guide). A workload whose access is by key and never by query belongs in DynamoDB, below. Note what this page does not claim: the database guide says Aurora has "up to five times the throughput of standard MySQL" and the Aurora user guide says "up to 6x"; two AWS pages disagree, so no throughput multiple is a reason here. |

## Key-value data

| | |
|---|---|
| **Recommended** | **Amazon DynamoDB.** |
| **Why** | The database guide gives DynamoDB "single-digit millisecond performance at any scale" for "workloads such as session stores or shopping carts" (database guide); there is "no practical limit on a table's size" ([Quotas in Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html)), and all data is encrypted at rest ([DynamoDB encryption at rest](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/EncryptionAtRest.html)). |
| **When not** | Access patterns not known in advance, or queries across entities: that is the "less predictable query patterns" the guide sends to Aurora. An item larger than the limit: "The maximum item size in DynamoDB is 400 KB" ([Constraints in Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html)) — store the body in S3 and the key in DynamoDB. |

## Secrets and configuration

| | |
|---|---|
| **Recommended** | **AWS Secrets Manager** for a credential: a database password, an API key, a token. **Systems Manager Parameter Store** for configuration that is not a secret. |
| **Why** | AWS's own comparison ([AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html), the table "Where should I store my application data?") gives Secrets Manager rotation "Automatic, with native database integrations" and Parameter Store rotation "None", and for database credentials, API keys and tokens says "we recommend AWS Secrets Manager". Rotation can be managed by Secrets Manager without a Lambda function, or done by one ([Rotate AWS Secrets Manager secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)). |
| **When not** | A value that is configuration, not a credential, goes to Parameter Store: its standard tier is free while Secrets Manager is billed per secret per month and per API call (comparison table). A `SecureString` parameter is encrypted with KMS and is acceptable for a sensitive value that has no rotation and no cross-account reader; cross-account sharing needs Parameter Store's advanced tier (same page). |

## Identity

| | |
|---|---|
| **Recommended** | **AWS IAM Identity Center** for people; **IAM roles** for workloads. |
| **Why** | The IAM best practices require federation with temporary credentials for people and roles for workloads, and recommend Identity Center ([Security best practices in IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)); [`docs/identity-and-access.md`](identity-and-access.md) has the argument. |
| **When not** | An application's own end users are not AWS identities: use the application's identity provider, and `ahrena-engineering-security:reviewing-access` for its checks. A third party that must call into the account gets a role with an external ID, not a user. A workload that cannot assume a role keeps a long-term key under the conditions in the same doc. |

## Networking and edge

| | |
|---|---|
| **Recommended** | A **VPC** with private subnets for compute and data; an **Application Load Balancer** in front of an HTTP service; **Amazon API Gateway HTTP API** in front of Lambda; **Amazon CloudFront** in front of public static content; gateway endpoints for S3 and DynamoDB. |
| **Why** | The networking guide gives VPC as a "private, isolated section of the AWS Cloud" and CloudFront as delivering content "with the lowest latency possible" ([Choosing an AWS networking and content delivery service](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-networking-and-content-delivery-service.html)). The ALB "functions at the application layer, the seventh layer" of the OSI model (compute guide), so it routes by path and host. API Gateway says "HTTP APIs are designed with minimal features" at a lower price ([Choose between REST APIs and HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html)). [`docs/networking.md`](networking.md) argues the VPC layout. |
| **When not** | A **Network Load Balancer**, which "functions at the fourth layer of the OSI model" (compute guide), for non-HTTP traffic. An API Gateway **REST API** when the API needs "API keys, per-client throttling, request validation, AWS WAF integration, or private API endpoints" (REST vs HTTP page). |

## Observability

| | |
|---|---|
| **Recommended** | **Amazon CloudWatch** for metrics, logs and alarms; **OpenTelemetry**, through the AWS Distro for OpenTelemetry or the CloudWatch agent, for traces and new instrumentation. |
| **Why** | CloudWatch "monitors your Amazon Web Services (AWS) resources and the applications you run on AWS in real time", with metrics, logs and alarms, and marks OpenTelemetry metrics as recommended over its classic metrics ([What is Amazon CloudWatch?](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)). The X-Ray SDKs and daemon entered maintenance mode on February 25, 2026, limited to security fixes, and AWS writes "We recommend to migrate to OpenTelemetry" ([X-Ray SDK and Daemon Support timeline](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-daemon-timeline.html)). |
| **When not** | Keep an existing X-Ray SDK where AWS's own instrumentation page still points to it — centralized sampling rules, and Lambda functions where the added memory and cold-start cost of ADOT matters ([Instrumenting your application for AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-instrumenting-your-app.html)). A project that already sends telemetry to another backend through OpenTelemetry keeps it. What a log line may contain is not this table's: [`rules/exposure.md`](../rules/exposure.md). |

## What the predecessor carried and this does not

The predecessor's catalog (`codex-aws-services`) listed several services per row and recommended none outright; this page names one and the case against it. Rows it had that are dropped: graph, time-series, wide-column, ML training and inference, edge functions, CI/CD services and Region choice. None is a problem every workload has, and a design that meets one reads the AWS decision guide for it ([AWS Decision Guides](https://docs.aws.amazon.com/decision-guides/)). Its Region advice named a client and a country and is client logic. Its figures ("up to 40% better cost-performance", "~7x") had no source and are not repeated.

## Where this stops

A recommendation here is a starting point for a design, not a rule: departing from it with a reason is a design decision, recorded as one. The page does not cover a client's existing estate, which the design reads first and keeps unless it has a reason to change. Service limits move; a design that depends on one re-reads the quota page cited beside it.
