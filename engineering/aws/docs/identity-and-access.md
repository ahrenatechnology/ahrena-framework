---
id: identity-and-access
type: doc
clade: engineering
subclade: aws
title: Identity and Access on AWS
summary: How IAM decides a request, which of AWS's own best practices the plugin's rule turns into conditions and which detector reports each, what an access-denied message carries and why that matters for exposure, and how a third party is given a role safely.
references:
  - rules/least-privilege.md
  - rules/exposure.md
  - docs/well-architected.md
---

# Identity and Access on AWS

This is the companion to [`rules/least-privilege.md`](../rules/least-privilege.md). The rule states the conditions; this explains where each comes from in AWS's own text, how IAM evaluates the policies the conditions are about, and which AWS service or scanner reports a breach. Every claim below cites the AWS page it was read from on 2026-11-14. A claim with no page is not here.

## What AWS itself recommends

AWS publishes fourteen IAM best practices, in this order, on [Security best practices in IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html):

1. Require human users to use federation with an identity provider to access AWS using temporary credentials.
2. Require workloads to use temporary credentials with IAM roles to access AWS.
3. Require multi-factor authentication (MFA).
4. Update access keys when needed for use cases that require long-term credentials.
5. Follow best practices to protect your root user credentials.
6. Apply least-privilege permissions.
7. Get started with AWS managed policies and move toward least-privilege permissions.
8. Use IAM Access Analyzer to generate least-privilege policies based on access activity.
9. Regularly review and remove unused users, roles, permissions, policies, and credentials.
10. Use conditions in IAM policies to further restrict access.
11. Verify public and cross-account access to resources with IAM Access Analyzer.
12. Use IAM Access Analyzer to validate your IAM policies for secure and functional permissions.
13. Establish permissions guardrails across multiple accounts.
14. Use permissions boundaries to delegate permissions management within an account.

The rule does not restate the list. It takes the ones a reader of a change can hold the change to — 1, 2, 6, 7, 10, 11 and 12 — and turns each into a condition with a detector. MFA (3) and the root user (5) are properties of an account, not of a change to an application or its infrastructure, so they are left to whoever owns the account; the rule's `Where this stops` says so.

The same practices appear in the Well-Architected security pillar as `SEC02-BP02 Use temporary credentials`, `SEC03-BP02 Grant least privilege access` and `SEC03-BP07 Analyze public and cross-account access` ([SEC 2](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-02.html), [SEC 3](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec-03.html)). [`docs/well-architected.md`](well-architected.md) places them in the pillar.

## How IAM decides a request

Four facts about evaluation decide how a policy has to be written and read.

**Nothing is allowed until something allows it.** "An IAM policy denies an IAM principal by default" ([Troubleshoot access denied error messages](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html)). A wildcard is therefore never needed to make a request work; it is only ever a choice to allow more than the request needed.

**An explicit deny wins.** "An explicit deny in either of these policies overrides the allow" ([Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)). Within one account the identity-based and resource-based policies combine as a union; a permissions boundary, a service control policy (SCP) and a resource control policy (RCP) each intersect with them.

**Guardrails grant nothing.** "No permissions are granted by an SCP" ([Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)), and "No permissions are granted by an RCP" ([Resource control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)). An SCP sets the maximum permissions for the IAM users and roles in member accounts; an RCP sets the maximum for resources, and is the one to use to restrict principals external to the organization. Neither applies to the management account or to service-linked roles. A permissions boundary is a managed policy that sets "the maximum permissions that an identity-based policy can grant to an IAM entity" ([Permissions boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)). The consequence for a review: a broad identity policy under a narrow boundary is still a broad policy, because the boundary can be detached and the policy cannot be read on its own.

**Conditions narrow a grant.** Best practice 10 names conditions; the [global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html) include `aws:PrincipalOrgID` (the organization the caller belongs to), `aws:SourceAccount` and `aws:SourceArn` (the resource on whose behalf an AWS service makes a service-to-service request) and `aws:SecureTransport` (whether the request used TLS). The page lists `aws:PrincipalOrgID` and `aws:SourceAccount` among the sensitive keys where a wildcard has no valid use.

## Temporary credentials, and where a long-term key remains

Access keys are "long-term credentials for an IAM user or the AWS account root user", and AWS recommends to "use temporary security credentials (such as IAM roles) instead of creating long-term credentials" ([Manage access keys for IAM users](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html)). The same page says not to create access keys with root credentials and not to place keys in application files or the project tree.

For people, the best-practices page recommends IAM Identity Center; Identity Center describes itself as "the AWS solution for connecting your workforce users" to AWS accounts and applications, and calls an organization instance the best practice ([What is IAM Identity Center?](https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html)).

The best-practices page also names the cases that still need a long-term key: a workload that cannot use a role, a third-party client that only accepts keys, and services such as CodeCommit and Amazon Keyspaces. That is why condition 3 of the rule asks for a role "where a role serves" and not for zero keys.

## The detectors

AWS ships three kinds of detector for these conditions, and the scanners most projects already run add a fourth.

**IAM Access Analyzer** ([overview](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html)) has three analyzers.

- *External access* finds resources "shared with an external entity" — outside the zone of trust, the account or the organization — by logic-based reasoning over resource policies. It covers S3 buckets and directory buckets, IAM roles, KMS keys, Lambda functions and layers, SQS queues, Secrets Manager secrets, SNS topics, EBS snapshots, RDS DB and cluster snapshots, ECR repositories, EFS file systems, and DynamoDB tables and streams. It is per Region.
- *Unused access* reports unused roles, access keys and passwords, and the unused services and actions of active ones. It is charged per IAM role and user analysed.
- *Internal access* covers a smaller set of resource types and is charged by resources monitored.

**Policy validation** ([Validate policies with IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-validation.html)) returns security warnings, errors, general warnings and suggestions for a policy before it is attached; the [check reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-reference-policy-checks.html) includes security warnings for `iam:PassRole` with a wildcard in the resource, and says there is no additional charge for these checks.

**AWS Config managed rules** evaluate deployed resources. The ones the rule names, each on its own page under `https://docs.aws.amazon.com/config/latest/developerguide/`:

| Config rule | What it reports |
|---|---|
| `iam-policy-no-statements-with-admin-access` | a customer managed policy that allows action `*` on resource `*`; inline and AWS managed policies are not evaluated |
| `iam-policy-no-statements-with-full-access` | a customer managed policy that grants a whole service, such as `ec2:*`; a prefix like `ec2:Describe*` passes |
| `iam-root-access-key-check` | a root user access key exists |
| `access-keys-rotated` | an active IAM user key older than `maxAccessKeyAge`, 90 days by default |
| `iam-user-unused-credentials-check` | a password or key unused for `maxCredentialUsageAge`, 90 days by default |
| `iam-user-no-policies-check` | a policy attached directly to a user rather than through a group or role |
| `s3-account-level-public-access-blocks-periodic` | the account-level S3 Block Public Access settings are off |
| `s3-bucket-level-public-access-prohibited` | a bucket made public at bucket level; `excludedPublicBuckets` lists the intended ones |
| `rds-instance-public-access-check` | a DB instance with `publiclyAccessible` true |
| `rds-snapshots-public-prohibited` | a public RDS snapshot |
| `lambda-function-public-access-prohibited` | a function resource policy with an empty or wildcard principal, or an S3 invoke without a source-account condition |
| `ec2-instance-no-public-ip` | an instance with a public IPv4 address |
| `restricted-ssh` | a security group allowing SSH from `0.0.0.0/0` or `::/0` |

The 90-day figures are the rules' own defaults, attributed to those pages; this plugin sets no number of its own.

**Scanners over infrastructure code** report the same states before deployment. Checkov ([policy index](https://www.checkov.io/5.Policy%20Index/terraform.html)): `CKV_AWS_1` (full `*-*` administrative privileges, on `aws_iam_policy_document`), `CKV_AWS_355` and `CKV_AWS_356` (`*` as a statement's resource for restrictable actions), `CKV_AWS_290` (write access without constraints), `CKV2_AWS_6` (S3 bucket without a public access block), `CKV_AWS_17` (RDS publicly accessible), `CKV_AWS_24` (port 22 from `0.0.0.0/0`). cdk-nag ([AwsSolutions rules](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md)): `AwsSolutions-IAM4` (an AWS managed policy is attached), `AwsSolutions-IAM5` (wildcard permissions without a suppression carrying evidence), `AwsSolutions-S2` (S3 public access not blocked), `AwsSolutions-EC23` (a security group open to `0.0.0.0/0` or `::/0`). In cdk-nag 3 a finding is acknowledged per finding with a `reason` string, `Validations.of(construct).acknowledge({ id: 'AwsSolutions-IAM5[Action::s3:*]', reason: '...' })` — which is exactly the recorded reason condition 2 of the rule asks for, kept beside the statement it excuses.

## Third parties and the confused deputy

When another party's account assumes a role in ours, the trust policy carries a condition on `sts:ExternalId`. AWS states that the external ID's "primary function" is to prevent the confused deputy problem, that it is not treated as a secret, and that the third party should generate one per customer account ([Access to AWS accounts owned by third parties](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html)). The reverse case — an AWS service acting on our resource — is narrowed with `aws:SourceArn` or `aws:SourceAccount`, which is what `lambda-function-public-access-prohibited` checks for an S3 invoke.

## What an access-denied message carries

This is the part of IAM the exposure rule exists for. AWS documents the shape of the message: "User {user} is not authorized to perform {action} on {resource} because {context}", where `{user}` "is the ARN of the principal that is denied access", the action is the service action, the resource is often present, and the context names the policy type that denied — an SCP, an RCP, a VPC endpoint policy, a permissions boundary, a session policy, a resource-based policy, a trust policy or an identity-based policy — and, for some types, that policy's ARN ([Troubleshoot access denied error messages](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html)).

So one message, returned as it came, tells its reader the account ID (inside the principal ARN), the role name, the action, the resource path, and which kind of guardrail governs the role. AWS says account IDs "are not considered secret, sensitive, or confidential information" but "should be used and shared carefully" ([View AWS account identifiers](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-identifiers.html)). The exposure rule does not rest on secrecy: it rests on the fact that a caller has no use for any of it, and that the message hands an outsider a map of the IAM configuration. [`rules/exposure.md`](../rules/exposure.md) holds the conditions.

For the person diagnosing it, the [IAM policy simulator](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html) evaluates identity-based policies, boundaries, SCPs and resource-based policies without sending a real request; it does not support RCPs, and its result can differ from the live environment.

## Where this stops

This document covers IAM as it bears on a workload and its infrastructure. It does not cover the account structure of a particular client — how many accounts, which organizational units, which SCPs — because that is client logic, not platform content (`ahrena-engineering-fundamentals:rules/client-logic.md`). It does not cover Amazon Cognito or any end-user identity for an application's own customers; that is the application's access discipline, `ahrena-engineering-security:reviewing-access`. Secrets storage is in [`docs/services.md`](services.md) and [`rules/data-protection.md`](../rules/data-protection.md).
