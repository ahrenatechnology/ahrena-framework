# AWS review conditions

The conditions `reviewing-aws` applies. Each gives the state, how it is detected, what exempts it, the correction, and where it comes from: a rule of this plugin, or the Well-Architected best practice and the AWS page behind it. A condition that a named scanner already decided on the change is not reported again; cite the scanner's result instead.

Grouped by pillar, as `docs/well-architected.md` describes.

## Security — identity and access

### IAM-1 Action `*` granted

- **State:** an `Allow` statement whose `Action` is `*`.
- **Detect:** every policy document, inline or managed, the change writes. Checkov `CKV_AWS_1`, cdk-nag `AwsSolutions-IAM5`.
- **Exempt:** none.
- **Correct:** list the actions the work calls.
- **Source:** `rules/least-privilege.md` condition 1.

### IAM-2 A whole service or every resource, with no recorded reason

- **State:** an `Allow` with `service:*`, or `Resource: "*"` on an action that supports resource-level permissions, and no cdk-nag acknowledgment with a `reason` or comment naming why the narrower form does not exist. Includes `iam:PassRole` on `*`.
- **Detect:** each policy statement; Checkov `CKV_AWS_355`, `CKV_AWS_356`, `CKV_AWS_290`; cdk-nag `AwsSolutions-IAM5`; IAM Access Analyzer policy validation if the project runs it.
- **Exempt:** an action that supports no resource-level permission, whose only resource is `*`; a prefix such as `s3:Get*`, which is IAM-4's question, not this.
- **Correct:** name the resources by ARN pattern, or record the reason beside the statement.
- **Source:** `rules/least-privilege.md` condition 2.

### IAM-3 A long-term key where a role serves

- **State:** an IAM user, access key or key pair created, stored or injected for a workload that runs on Lambda, ECS, EKS or EC2; an access key read from configuration by code running on AWS compute; a root access key.
- **Detect:** IAM user and access-key resources; environment and secret entries named for an access key ID or secret access key; SDK clients built with explicit keys.
- **Exempt:** a case AWS names as needing a long-term key — a workload that cannot assume a role, a third-party client that accepts only keys — with the case written down.
- **Correct:** give the compute a role and let the SDK's default credential chain read it.
- **Source:** `rules/least-privilege.md` conditions 3 and 4; IAM best practices 1 and 2.

### IAM-4 A grant broader than the work

- **State:** an AWS managed policy attached to a workload role; a prefix wildcard (`s3:Get*`) where the code calls one or two actions; a permission no code path in the change uses.
- **Detect:** compare the actions the role is granted with the SDK calls the workload makes. cdk-nag `AwsSolutions-IAM4` reports the managed policy.
- **Exempt:** a managed policy whose every action the workload calls, recorded as such beside the attachment.
- **Correct:** replace with a customer managed policy listing the actions used.
- **Source:** IAM best practices 6 and 7; `SEC03-BP02` ([Security best practices in IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)). Deferrable unless it is IAM-1 or IAM-2.

### IAM-5 Reachable from outside the account

- **State:** an S3 bucket without Block Public Access; a public RDS instance or snapshot; a Lambda resource policy with an empty or `*` principal; a public IP on an instance outside a public-facing tier; a security group admitting `0.0.0.0/0` or `::/0` to SSH, RDP or a database port; a resource policy granting another account without the change saying why.
- **Detect:** Checkov `CKV2_AWS_6`, `CKV_AWS_17`, `CKV_AWS_24`, `CKV_AWS_25`; cdk-nag `AwsSolutions-S2`, `AwsSolutions-EC23`; after deployment Config rules and the IAM Access Analyzer external access analyzer, as `rules/least-privilege.md` condition 5 lists.
- **Exempt:** a resource whose purpose is public, with the reason recorded where the detector reads it (Config's `excludedPublicBuckets`, a scanner acknowledgment).
- **Correct:** block public access; reach an instance through Session Manager; reach the database from the application's security group only.
- **Source:** `rules/least-privilege.md` condition 5.

### IAM-6 A trust or resource policy without its condition

- **State:** a role trusted by a third party's account with no `sts:ExternalId` condition; a resource policy admitting an AWS service principal without `aws:SourceArn` or `aws:SourceAccount`.
- **Detect:** every `AssumeRolePolicyDocument` and resource policy the change writes.
- **Exempt:** a role trusted only by accounts of the same organization, narrowed by `aws:PrincipalOrgID`.
- **Correct:** add the condition.
- **Source:** `rules/least-privilege.md` condition 6.

## Security — data

### ENC-1 A store created unencrypted

- **State:** an RDS or Aurora instance or cluster without storage encryption; an EBS volume unencrypted; an SNS topic carrying non-public data without a KMS key.
- **Detect:** Checkov `CKV_AWS_16`, `CKV_AWS_3`; cdk-nag `AwsSolutions-RDS2`; Config `rds-storage-encrypted`, `encrypted-volumes`, `sns-encrypted-kms`.
- **Exempt:** S3 and DynamoDB, which are always encrypted at rest.
- **Correct:** set encryption at creation. For an RDS instance that already exists unencrypted, encryption cannot be turned on in place: restore from an encrypted snapshot copy or use a blue/green deployment, and plan it as a migration.
- **Source:** `rules/data-protection.md` condition 1.

### ENC-2 Plain transport

- **State:** an S3 bucket with no policy denying `aws:SecureTransport` false; an ALB HTTP listener that forwards instead of redirecting; an OpenSearch domain not enforcing HTTPS; a client built with TLS verification off.
- **Detect:** cdk-nag `AwsSolutions-S10`; Config `s3-bucket-ssl-requests-only`, `alb-http-to-https-redirection-check`, `opensearch-https-required`.
- **Exempt:** a health-check listener inside the VPC that the load balancer alone reaches.
- **Correct:** add the deny statement; redirect HTTP to HTTPS; enforce HTTPS.
- **Source:** `rules/data-protection.md` conditions 2 and 3.

### ENC-3 A TLS policy left to the tool's default

- **State:** an HTTPS listener with no security policy named in the code.
- **Detect:** each `HTTPS` or `TLS` listener resource.
- **Exempt:** none.
- **Correct:** name the policy, chosen from the current list on AWS's page for ALB security policies, and record why.
- **Source:** `rules/data-protection.md` condition 3.

### ENC-4 A credential outside Secrets Manager

- **State:** a database password, API key or token in a task definition's or function's plain environment, in EC2 user data, in a Parameter Store `String`, or in a committed file.
- **Detect:** environment blocks and user data the change writes; names that read like credentials. A literal value is `reviewing-secrets`'s `SEC-n`, not this.
- **Exempt:** a value that is configuration and not a credential.
- **Correct:** store it in Secrets Manager and read it from there at run time, with rotation where the secret supports it.
- **Source:** `rules/data-protection.md` condition 4; `SEC02-BP03`.

## Security — exposure

### EXP-1 An AWS SDK error returned as it came

- **State:** a handler, CLI or tool that catches an error from an AWS SDK call and returns its message, its string form, its body or the exception object to the caller.
- **Detect:** every `except`, `catch` or error branch around an AWS SDK call in the change, and what the branch puts in the response.
- **Exempt:** none in code a caller reaches.
- **Correct:** return a generic error and the application's correlation ID; log the operation, the service's error code and the correlation ID as named fields.
- **Source:** `rules/exposure.md` condition 1. **Blocking.** This is the incident behind issue 294.

### EXP-2 AWS detail in what a caller reads

- **State:** a response, a page, a CLI result or a tool result that carries an account ID, an ARN, a role, bucket, table, queue, secret or key name, a VPC or subnet identifier, or a policy.
- **Detect:** each response the change builds and where its fields come from — an environment variable, a describe call, a configuration object.
- **Exempt:** an application whose purpose is to show the account owner their own AWS resources, as `rules/exposure.md` describes.
- **Correct:** return the application's own identifier for the thing, and keep the mapping to AWS inside the AWS layer.
- **Source:** `rules/exposure.md` condition 2. Blocking.

### EXP-3 A whole AWS object in a log or trace

- **State:** a logger, span or metric given a whole SDK response, exception or policy document.
- **Detect:** every log and tracing call in the AWS layer, and what it is handed.
- **Exempt:** a log of named fields — operation, error code, correlation ID.
- **Correct:** log the named fields.
- **Source:** `rules/exposure.md` condition 3.

### EXP-4 A generated policy that leaves the AWS layer

- **State:** application code that builds a policy document and returns, prints or logs it.
- **Detect:** code that assembles `Statement`, `Effect` and `Action` structures.
- **Exempt:** handing it to the AWS API.
- **Correct:** pass it to the API only.
- **Source:** `rules/exposure.md` condition 4.

## Cost

### CST-1 A resource without the owner tag

- **State:** a resource that accepts tags created without the project's owner tag key, or with an empty value.
- **Detect:** every taggable resource in the change, against the key the project declares; inherited stack- or provider-level default tags count.
- **Exempt:** a resource AWS creates on the workload's behalf.
- **Correct:** add the tag, preferably as a default at the stack or provider level.
- **Source:** `rules/cost-ownership.md` condition 1.

### CST-2 An account without a budget signal

- **State:** a change that creates an account or environment and no cost budget with a forecast alert.
- **Detect:** the change creates an account, or the design names one with no budget.
- **Exempt:** an account whose budget the project shows already exists.
- **Correct:** add an AWS Budgets cost budget with a forecast alert to the owner.
- **Source:** `rules/cost-ownership.md` condition 3.

### CST-3 A log group kept forever

- **State:** a CloudWatch log group created with no retention, which AWS keeps "indefinitely" ([Working with log groups and log streams](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)).
- **Detect:** each log group resource, and each function or service whose log group the platform creates implicitly. Config `cw-loggroup-retention-period-check` does not detect this: it treats never-expire as compliant.
- **Exempt:** a log group that must be kept indefinitely for a stated obligation.
- **Correct:** set the retention the project's obligations require.
- **Source:** `COST04` and `docs/cost.md`. Deferrable.

### CST-4 AWS-service traffic through NAT

- **State:** a private subnet that reaches S3 or DynamoDB with no gateway endpoint, so the traffic is processed and charged by the NAT gateway.
- **Detect:** route tables and endpoints in the change against the services the workload calls.
- **Exempt:** a VPC with no NAT gateway.
- **Correct:** add a gateway endpoint, which carries no additional charge ([Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)).
- **Source:** `docs/networking.md`, `docs/cost.md`. Deferrable.

## Reliability

### REL-1 A production workload in one place

- **State:** a production service, database or NAT gateway in a single Availability Zone, with no recorded decision that an outage of that zone is accepted.
- **Detect:** subnet lists, `MultiAZ` settings, desired counts and NAT placement.
- **Exempt:** a non-production environment; a recorded decision.
- **Correct:** spread across at least two zones, or record the decision. Which is right is a question for the project when the design does not say.
- **Source:** `REL10-BP01 Deploy the workload to multiple locations` ([REL 10](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-10.html)); NAT per zone from [NAT gateway basics](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html).

### REL-2 A store with no backup

- **State:** a database or file system with automated backups off, or with backups not encrypted.
- **Detect:** backup retention and backup plan settings on each store the change creates.
- **Exempt:** a store whose data is reproduced from another source, as REL09-BP01 allows, with the source named.
- **Correct:** enable automated backups with the retention the project's recovery objective needs.
- **Source:** `REL09-BP01` and `REL09-BP02` ([REL 9](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-09.html)).
