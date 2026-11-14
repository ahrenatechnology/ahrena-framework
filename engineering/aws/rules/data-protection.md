---
id: data-protection
type: rule
clade: engineering
subclade: aws
title: Data Protection on AWS
statement: AWS data is encrypted at rest, reached only over TLS, behind a TLS policy the code names, and every credential lives in Secrets Manager, never in config.
enforcement: judgment
references:
  - docs/well-architected.md
  - docs/services.md
  - docs/networking.md
---

# Data Protection on AWS

Data a workload stores on AWS is encrypted at rest from the moment the store is created; data it moves is reachable only over TLS; and a credential it needs is read from Secrets Manager at run time rather than travelling in its configuration.

The rule traces to Well-Architected `SEC08-BP02 Enforce encryption at rest`, `SEC09-BP02 Enforce encryption in transit` and `SEC02-BP03 Store and use secrets securely` ([`docs/well-architected.md`](../docs/well-architected.md)). The AWS pages for each service's behaviour are cited below where a condition depends on it; which service holds a secret is argued in [`docs/services.md`](../docs/services.md).

## Conditions

1. **Every store the change creates is encrypted at rest.**
   - **RDS and Aurora** set storage encryption at creation. AWS: "You can only encrypt an Amazon RDS DB instance when you create it, not after the DB instance is created" ([Encrypting Amazon RDS resources](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html)); an unencrypted instance is encrypted by restoring an encrypted copy of a snapshot, or by a blue/green deployment. Decided by Checkov `CKV_AWS_16`, cdk-nag `AwsSolutions-RDS2` and Config `rds-storage-encrypted`.
   - **EBS** is encrypted. EBS encryption by default "is a Region-specific setting", applies to new volumes only, and can be enabled per account and Region ([Enable Amazon EBS encryption by default](https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html)). Decided by Checkov `CKV_AWS_3` and Config `encrypted-volumes` and `ec2-ebs-encryption-by-default`.
   - **SNS topics** that carry anything but public data name a KMS key. Decided by Config `sns-encrypted-kms`.
   - **Any other store** the change creates — a queue, a cache, a file system — has the encryption at rest its service offers enabled, set in the code rather than left to a default the reader cannot see. Decided by review, against the service's own page.
   - **S3** and **DynamoDB** need nothing: every new S3 object has been encrypted since January 5, 2023 and that "can no longer" be disabled ([Default encryption FAQ](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-encryption-faq.html)), and "all user data stored in Amazon DynamoDB is fully encrypted at rest" ([DynamoDB encryption at rest](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/EncryptionAtRest.html)). A change that names a KMS key for either is choosing the key, not turning encryption on; condition 5 covers that choice.
2. **Every S3 bucket the change creates denies a request not sent over TLS**, by a bucket policy statement on `aws:SecureTransport` ([Security best practices for Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)). Decided by cdk-nag `AwsSolutions-S10` and Config `s3-bucket-ssl-requests-only`.
3. **Every listener that faces a client speaks TLS, and names its security policy.** An Application Load Balancer's HTTP listener only redirects to HTTPS (Config `alb-http-to-https-redirection-check`); an HTTPS listener names its TLS security policy in the code rather than inheriting a tool's default, because the defaults differ — the console gives `ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09`, while the CLI, CloudFormation and CDK give `ELBSecurityPolicy-2016-08` ([Security policies for your Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/describe-ssl-policies.html)). An OpenSearch domain enforces HTTPS (Config `opensearch-https-required`). Which policy is named is decided by review; that one is named is decided by reading the listener.
4. **A credential a workload needs is stored in Secrets Manager and read at run time.** It is not a literal in code, an unencrypted environment variable in a task definition or function configuration, EC2 user data, a Systems Manager parameter of either type, or a committed file. A secret that supports rotation has it scheduled (Config `secretsmanager-rotation-enabled-check`). A literal credential anywhere in a change is reported by `ahrena-engineering-security:reviewing-secrets`; the rest is decided by review.
5. **A store whose data must be readable only by named principals beyond what IAM grants uses a customer managed KMS key whose key policy names them.** An AWS managed key's policy is "Controlled by service; viewable by customer", while a customer managed key's is "Exclusively controlled by the customer" ([AWS KMS keys](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)). Decided by review, from what the design says about who may read the data.

## Where this stops

**Not every store needs a customer managed key.** Condition 5 applies when the data's readers must be restricted by the key; otherwise the AWS owned or AWS managed key that encrypts the store is sufficient, and adding a key adds a policy to maintain and a per-key cost. The predecessor's "SSE-KMS everywhere, customer-managed preferably" is not kept.

**Which TLS policy is not fixed here.** The rule requires that the policy be chosen in the code; it does not pick one, because AWS publishes and retires policies and a name fixed in this rule would go stale. The design records which it chose and why.

**Data inside the application is not this rule's.** What a log line, a response or an error may carry is [`rules/exposure.md`](exposure.md); whether a field should be stored at all is `ahrena-engineering-security:reviewing-sensitive-data`.

**Backups and their encryption** are reliability (`REL09-BP02 Secure and encrypt backups`), held as review condition `REL-2`.
