---
id: cost
type: doc
clade: engineering
subclade: aws
title: Cost on AWS
summary: How a workload's spend is attributed and watched on AWS — tags and their activation, budgets and anomaly detection, the services that recommend a smaller footprint, and the defaults that cost money silently — with what AWS documents for each and why the predecessor's dollar figures are not here.
references:
  - rules/cost-ownership.md
  - docs/well-architected.md
  - docs/networking.md
---

# Cost on AWS

This is the companion to [`rules/cost-ownership.md`](../rules/cost-ownership.md). The rule asks two things of every resource: that someone owns it by tag, and that the account it lives in has a budget that will say when spend runs away. This explains how AWS makes each of those work, what it does not do on its own, and the defaults that cost money unless someone changes them. Every claim cites the AWS page it was read from on 2026-11-14.

## Why ownership and a budget, and nothing more

The cost optimization pillar's design principles are "Implement Cloud Financial Management", "Adopt a consumption model", "Measure overall efficiency", "Stop spending money on undifferentiated heavy lifting" and "Analyze and attribute expenditure" ([Design principles](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-dp.html)). Its best practices include `COST02-BP05 Implement cost controls`, `COST03-BP02 Add organization information to cost and usage`, `COST03-BP05 Configure billing and cost management tools` and the decommissioning question `COST 4` ([COST 2](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-02.html), [COST 3](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-03.html), [COST 4](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-04.html)).

Two of those can be held against a single change: the resource it adds is attributed to an owner (COST03-BP02), and the account has a control that reports spend (COST02-BP05, COST03-BP05). Everything else in the pillar — right-sizing, commitment purchases, decommissioning — is a periodic decision about a running estate, made with the data those two produce. A rule cannot decide it from a diff, so the rule stops at the two and this document carries the rest as reference.

## Tags: what attributes a cost, and what does not

A tag on a resource does not reach the bill until its key is activated: "For tags to appear on your billing reports, you must activate them", and it "can take up to 24 hours for the tag keys to appear" on the cost allocation tags page and up to 24 more to activate ([Activating user-defined cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)). The page says nothing about whether activation applies to earlier usage, so this plugin assumes it does not and asks for activation when the key is introduced.

**Tag policies do not stop an untagged resource.** AWS Organizations tag policies "standardize the tags attached to the AWS resources" and can prevent a noncompliant *tagging* request on the resource types chosen for enforcement, but "untagged resources or tags that aren't defined in the tag policy aren't evaluated" ([Tag policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)). The predecessor's "resources without tags are blocked by SCP or Config Rule" therefore names one mechanism that does not do it.

**What reports a missing tag** is the AWS Config managed rule `required-tags`: `tag1Key` is required (its default is `CostCenter`, so it must be set to the project's owner key), up to six keys can be required, and it covers only the resource types its page lists ([required-tags](https://docs.aws.amazon.com/config/latest/developerguide/required-tags.html)). Before deployment, the infrastructure code is read by review: no Checkov or cdk-nag check found on 2026-11-14 decides "every resource carries tag X" generically.

**Which key.** The rule requires one owner key and leaves its name to the project, because a project that already tags `team` or `owner` should not carry a second key that says the same. The predecessor required four (`CostCenter`, `Environment`, `Project`, `Owner`); the AWS pages read here do not prescribe a set, and the predecessor gave no source for its four.

## Budgets and anomaly detection

AWS Budgets has six budget types — cost, usage, RI utilization, RI coverage, Savings Plans utilization and Savings Plans coverage — and alerts "for both actual (after accruing) and forecasted (before accruing) spends"; a budget action can, for example, apply an IAM policy that denies provisioning more resources. The page warns of a delay between incurring a charge and being notified ([Managing your costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)).

Cost Anomaly Detection "uses machine learning models to detect and alert on anomalous spend patterns", with root causes ranked by impact and alerts by email or SNS ([Detecting unusual spend with AWS Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/manage-ad.html)).

**The rule asks for a cost budget with an alert on actual and on forecasted spend.** The forecast alert is the one that arrives before the money is spent, which is the point of a signal. The thresholds of the alert are the project's: the predecessor's 50, 80 and 100 percent had no source, and none of the pages read prescribes a figure. Anomaly detection is recommended in addition and not required, because it needs history to learn from and says nothing in a new account.

## Services that recommend a smaller footprint

- **AWS Compute Optimizer** recommends for EC2 instances and Auto Scaling groups, EBS volumes, Lambda functions, ECS services on Fargate, commercial software licenses, Aurora and RDS, NAT gateways, DynamoDB, ElastiCache, MemoryDB, DocumentDB, WorkSpaces and SageMaker, at no additional cost for its default metrics ([What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)).
- **Savings Plans** come in four types — Compute, Database, EC2 Instance and SageMaker AI — on 1- or 3-year terms ([Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)). A commitment is a decision about steady usage over a term, which a design cannot make before the usage exists.
- **S3 Intelligent-Tiering** is the "recommended storage class for data with unknown, changing, or unpredictable access patterns", with no retrieval charges and "a small monthly object monitoring and automation charge" ([Managing storage costs with Amazon S3 Intelligent-Tiering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html)).

## Defaults that cost money silently

**Log retention.** "By default, log data is stored in CloudWatch Logs indefinitely" ([Working with log groups and log streams](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)). Note the trap in the obvious detector: Config's `cw-loggroup-retention-period-check` treats "never expire" as compliant, because it checks for at least `MinRetentionTime` (365 days by default) — it guards against too short, not against forever ([cw-loggroup-retention-period-check](https://docs.aws.amazon.com/config/latest/developerguide/cw-loggroup-retention-period-check.html)); Checkov `CKV_AWS_338` likewise asks for at least one year. A log group with no retention set is therefore found by review (`CST-3`), and the value chosen is the project's, from its own retention obligations.

**NAT for AWS-service traffic.** NAT is charged per hour and per GB processed, and gateway endpoints for S3 and DynamoDB carry no additional charge ([NAT pricing](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html), [Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)); [`docs/networking.md`](networking.md) has the routing. The other side of the trade is in the same document: AWS recommends a NAT gateway per Availability Zone for resiliency. A non-production environment that accepts one zone's outage may run one, and writes that it did.

## What the predecessor carried and this does not

The predecessor's cost law quoted monthly prices (an instance "US$ 800/month", NAT "~US$ 32/month/AZ", Elastic IP "~US$ 3.6/month"), ratios ("on-demand is ~7x more expensive"), a "70%+" commitment-coverage target, a ">US$ 100/month" decision threshold and a "<15%" variance metric. None carried a source or a date, prices vary by Region and change, and none of the AWS pages read on 2026-11-14 states them. They are left out under the framework's standard that a threshold is measured, attributed, or absent. A design that needs a figure gets it from the AWS Pricing Calculator for its own Region and usage, on the day, and records it in the design.

## Where this stops

This document does not set a project's budget amount, alert thresholds, retention periods or tag key; those are the project's and are recorded in its own configuration. It does not cover billing across a client's accounts or organization, which is client logic (`ahrena-engineering-fundamentals:rules/client-logic.md`). Pricing for a specific design is computed for that design, not stored here.
