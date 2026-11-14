---
id: exposure
type: rule
clade: engineering
subclade: aws
title: No AWS Detail in an Application's Output
statement: App code never outputs or logs a raw AWS SDK error, IAM policy, ARN, account ID or resource layout; the caller gets a generic error and an ID.
enforcement: judgment
references:
  - docs/identity-and-access.md
---

# No AWS Detail in an Application's Output

An application that runs on AWS keeps what it knows about its own AWS configuration inside the layer that calls AWS. What leaves that layer — to a caller, a screen, a log or a trace — is an allowlist of named fields, and none of them is an account ID, an ARN, an IAM policy, a role or resource name, or the text of an error AWS returned.

This is the AWS form of the framework's exposure rule, issue 294 of this repository: nothing sensitive leaves the layer that owns it, and what a layer emits is an allowlist. That rule is language- and vendor-agnostic; this one names what is sensitive on AWS and where it hides. The incident behind both was an HTTP 500 whose body was a cloud SDK's access-denied message, verbatim, from which the caller read the account ID, the role, the denied action, the resource path and the kind of guardrail on the role.

[`docs/identity-and-access.md`](../docs/identity-and-access.md) shows why that one message is enough: AWS documents that an access-denied message carries "the ARN of the principal that is denied access", the action, often the resource, and the type of policy that denied it ([Troubleshoot access denied error messages](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html)). AWS also says account IDs "are not considered secret, sensitive, or confidential information" but "should be used and shared carefully" ([View AWS account identifiers](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-identifiers.html)); this rule does not rest on secrecy. It rests on the caller having no use for any of it, and on the message handing an outsider a map of the IAM configuration.

## What counts

**AWS detail** is: an account ID; an ARN of any principal or resource; an IAM, resource, trust, SCP, RCP or key policy document, or any statement of one; the name of a role, user, bucket, queue, table, secret, parameter, key, stack, cluster, function or log group; a VPC, subnet, security group or endpoint identifier or address; a Region where the application does not choose to state it; and the message, body or whole object of an error or response an AWS SDK returned.

**An exit** is: an HTTP response body or header, a GraphQL or RPC error, a CLI's standard output or error, a tool or agent result, a page or message shown to a user, a log record, a trace or span attribute, a metric dimension, and an event published outside the service.

## Conditions

1. **No AWS SDK error reaches a caller as it came.** A handler that catches an error from an AWS SDK call returns a generic error and a correlation ID; it does not return the error's message, its string form, its serialised body or the exception object, in any exit a caller reads. Decided by review, as condition `EXP-1` of `skills/reviewing-aws`.
2. **No exit a caller reads carries AWS detail.** A response, a CLI result, a tool result or a user-facing message names no item in the list above, whether it came from an error, a configuration object, an environment variable or a describe call. Decided by review, as `EXP-2`.
3. **No log, trace or metric is given a whole AWS SDK response, exception or policy document.** The layer that calls AWS logs named fields — the operation, the service's error code, the correlation ID — and not the object. A policy document is never logged. Decided by review, as `EXP-3`.
4. **No IAM policy is built or printed by application code for a reader outside the AWS layer.** Code that generates a policy (for a presigned grant, a session policy, a tenant-scoped role) hands it to the AWS API and to nothing else. Decided by review, as `EXP-4`.

A CloudWatch Logs data protection policy is a backstop for one class of what leaks into logs and not a detector for this rule: it masks sensitive data at ingestion, including AWS secret access keys through the managed identifier `AwsSecretKey`, but it has no identifier for an ARN, an account ID or a policy, and it does not mask events ingested before it was attached ([Help protect sensitive log data with masking](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/mask-sensitive-log-data.html), [Credentials](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/protect-sensitive-log-data-types-credentials.html)).

## Where this stops

**The AWS layer and its operators may see the detail.** A deployment pipeline, an infrastructure plan, a CloudTrail record and the account's own operators working inside the account are where AWS detail belongs, and this rule does not reach them. A diagnosis written up in an issue, a pull request or a message leaves the account and is an exit. Infrastructure outputs and plans are governed by the exposure rule of issue 294 and by the infrastructure-as-code plugin, not here.

**A correlation ID is not AWS detail.** The application's own request ID, returned to the caller and written to the log beside the named fields, is what lets an operator find the failure without the caller seeing it.

**An application whose subject is AWS may show AWS detail to the account's own owner.** A console, an account inventory or a cost report built for the people who own the account displays ARNs on purpose. The condition is then about whose account: showing a tenant another tenant's, or the platform's own, is the breach, and that is `ahrena-engineering-security:reviewing-access`.

**No detector here decides these conditions.** They need a reader who can tell an error object from a message built for the caller. The language-agnostic hook that issue 294 adds reports the pass-through of a whole error or upstream response in any language; once it lands, conditions 1 and 3 have a hook in front of review.
