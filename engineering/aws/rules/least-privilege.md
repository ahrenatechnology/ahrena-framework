---
id: least-privilege
type: rule
clade: engineering
subclade: aws
title: Least Privilege on AWS
statement: AWS grants no wildcard action or resource without a recorded reason, uses roles not long-lived keys where a role serves, and makes nothing public by default.
enforcement: judgment
references:
  - docs/identity-and-access.md
  - docs/networking.md
---

# Least Privilege on AWS

A principal on AWS is granted what its work needs and nothing more; a credential is temporary wherever AWS can issue one; and a resource is reachable from outside the account only when someone decided it should be and wrote down why.

The rationale, the evaluation logic behind each condition and the AWS page for every claim are in [`docs/identity-and-access.md`](../docs/identity-and-access.md). The conditions below hold for any change that writes or edits an IAM policy, a trust policy, a resource-based policy, a security group, or the public-access setting of a resource — in CloudFormation, CDK, Terraform, an SDK call or a console runbook alike.

## Conditions

1. **No `Allow` statement grants action `*`.** On resource `*` it is decided before deployment by Checkov `CKV_AWS_1` and after deployment by the AWS Config rule `iam-policy-no-statements-with-admin-access`, which reads customer managed policies only. On a narrower resource, and in an inline or AWS managed policy, it is decided by cdk-nag `AwsSolutions-IAM5` where the project runs it, and by review.
2. **No `Allow` statement grants a whole service (`service:*`) or resource `*` on an action that supports resource-level permissions, unless the reason is recorded beside the statement.** A recorded reason is a cdk-nag acknowledgment whose `reason` names the evidence, or a comment on the statement naming why the narrower form does not exist. Decided by cdk-nag `AwsSolutions-IAM5`, Checkov `CKV_AWS_355` and `CKV_AWS_356`, IAM Access Analyzer policy validation (its security warnings include `iam:PassRole` with a wildcard resource), and Config `iam-policy-no-statements-with-full-access`; whether a recorded reason is a reason is decided by review.
3. **A workload that runs on AWS compute reads its credentials from the role it runs under, and no IAM user access key is created, stored or injected for it.** No root user access key exists. Decided by review for the workload; by Config `iam-root-access-key-check` for root. A key that remains for a case AWS names as needing one — a workload that cannot assume a role, a third-party client that accepts only keys — is reported when stale by Config `access-keys-rotated` and `iam-user-unused-credentials-check`, at their default of 90 days, and by IAM Access Analyzer unused access.
4. **A person reaches AWS through federation with temporary credentials, and no IAM user is created for a person.** Decided by review.
5. **No resource is reachable from outside the account unless a recorded reason says it should be.** This covers an S3 bucket without Block Public Access, an RDS instance or snapshot that is public, a Lambda function whose resource policy has an empty or wildcard principal, an EC2 instance with a public address outside a public-facing tier, and a security group that admits `0.0.0.0/0` or `::/0` to an administrative port. Decided before deployment by Checkov `CKV2_AWS_6`, `CKV_AWS_17`, `CKV_AWS_24` and cdk-nag `AwsSolutions-S2`, `AwsSolutions-EC23`; after deployment by Config `s3-account-level-public-access-blocks-periodic`, `s3-bucket-level-public-access-prohibited` (whose `excludedPublicBuckets` parameter is where an intended public bucket is recorded), `rds-instance-public-access-check`, `rds-snapshots-public-prohibited`, `lambda-function-public-access-prohibited`, `ec2-instance-no-public-ip` and `restricted-ssh`; and by the IAM Access Analyzer external access analyzer for every resource type it covers.
6. **A role another account assumes requires `sts:ExternalId` in its trust policy when that account is a third party, and a resource policy that admits an AWS service principal is conditioned on `aws:SourceArn` or `aws:SourceAccount`.** Decided by review; for a Lambda function invoked by S3, by Config `lambda-function-public-access-prohibited`.

## Where this stops

**The account itself is not a change.** MFA for people, protection of the root user's password, the organization's SCPs and RCPs, and which accounts exist are properties of the account a client owns, and how a client structures them is client logic (`ahrena-engineering-fundamentals:rules/client-logic.md`). This rule reaches a root access key only because Config decides it in one line, and stops there.

**An AWS managed policy is not a breach of this rule by itself.** AWS's own best practice is to start from managed policies and move toward least privilege, and cdk-nag `AwsSolutions-IAM4` reports every one. A managed policy attached to a workload role is a review finding (`IAM-4`) because it is usually broader than the work; it is a rule breach only when it grants what conditions 1 or 2 forbid.

**A wildcard that cannot be narrowed is allowed with its reason.** Some actions do not support resource-level permissions, and for those `*` is the only resource there is; condition 2 excludes them by construction. A prefix such as `s3:Get*` is not a whole-service grant and Config passes it; whether it is still too broad is review.

**This rule does not check that a policy is sufficient.** A policy that grants too little fails at run time with an access-denied error; that is a deployment failure, diagnosed by `skills/diagnosing-aws-deployments`, and not a defect this rule exists to prevent.

**This rule does not reach an application's own users.** Who may read whose record in the application is `ahrena-engineering-security:reviewing-access`.
