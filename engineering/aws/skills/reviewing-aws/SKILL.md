---
name: reviewing-aws
description: Use when a change under review touches AWS - application code that calls an AWS SDK, or infrastructure code that declares AWS resources (CloudFormation, CDK, Terraform's AWS provider, an IAM policy document) - and the question is what an AWS reader would catch - a wildcard grant, a long-lived key where a role serves, a public resource, an unencrypted store, an AWS SDK error or ARN handed back to a caller, a resource with no owner tag. Reads the routed files against this plugin's rules and the conditions below; every finding names the condition.
type: skill
clade: engineering
subclade: aws
references:
  - rules/least-privilege.md
  - rules/data-protection.md
  - rules/exposure.md
  - rules/cost-ownership.md
  - docs/well-architected.md
  - docs/identity-and-access.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing AWS

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` and the language skill for the changed files have read what holds in any cloud. This skill reads what needs an AWS reader: the identity, data, exposure and cost conditions of this plugin's four rules, and the reliability conditions the Well-Architected framework gives a change.

The conditions are in `references/conditions.md`, identified by a prefix and a number (`IAM-n`, `ENC-n`, `EXP-n`, `CST-n`, `REL-n`) and grouped by pillar. A finding cites the identifier. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the project first

This plugin ships its route fragment, `review-routes.json` at the plugin root; the router reads it when it is named by `--plugin-routes` or listed in `ROUTE_REVIEW_FRAGMENTS`, as `ahrena-engineering-quality:docs/review-routes.md` describes. If the router ran without it and the change touches AWS, open this skill anyway and say in the review that the route was not supplied. Four routes select this skill:

| Route | Fires on | Opens |
|---|---|---|
| `aws-application` | an added source line that imports or calls an AWS SDK or the CDK, handles an AWS SDK error, or writes an ARN | the four rules, `EXP-n` first |
| `aws-templates` | a CloudFormation or SAM template | the identity, data and cost rules, every group of conditions |
| `aws-terraform` | a Terraform file that declares an AWS resource or the AWS provider | the same |
| `aws-policy-documents` | a JSON file holding an IAM policy document | `rules/least-privilege.md`, conditions `IAM-n` |

Before the checklist, read how this project uses AWS: its infrastructure directory, the tool it deploys with, the owner tag key and environments it declares, and any scanner its pipeline runs (Checkov, cdk-nag, cfn-lint) with that run's result. A condition a green scanner already decided on this change is settled; cite the scanner's check and move on.

## 2. Open the conditions the change calls for

| What the change touches | Conditions |
|---|---|
| a handler, CLI or tool that calls an AWS SDK | `EXP-1` to `EXP-4` |
| a policy, role, user, trust policy or resource policy | `IAM-1` to `IAM-6` |
| a security group, subnet, route table, endpoint or public-access setting | `IAM-5`, `CST-4` |
| a database, volume, bucket, topic, listener or secret | `ENC-1` to `ENC-4`, `REL-2` |
| any taggable resource, an account or environment, a log group | `CST-1` to `CST-3` |
| a production service, database or NAT gateway | `REL-1` |

`EXP-1` is read on every route that fires on application code, whatever else the change touches: it is the condition behind issue 294.

## 3. Read beyond the hunk

For a policy, find every principal that holds it and every code path that uses the role, so `IAM-4` compares what is granted with what is called. For an error branch, follow the error to the outermost handler: an SDK error caught and re-raised three layers down still reaches the caller if the top handler serialises it. For a resource, read the stack- or provider-level defaults the diff does not show — default tags, default encryption, default listener policy.

Read what the change replaced, from the base revision, before calling a changed line wrong.

## 4. Apply the routed conditions

Work condition by condition. For each candidate, state the scenario in AWS terms: the principal and the request, the resource and who can reach it, or the caller and the bytes they receive. A condition whose answer depends on a decision the project has not written down — whether a bucket is meant to be public, whether a zone outage is accepted — is a `question`, naming who answers it.

Read each condition's `Exempt` line and drop what it excludes. Where the project records a reason (a cdk-nag acknowledgment, `excludedPublicBuckets`, a comment), read the reason: one that names no evidence is reported as the condition it was meant to excuse.

A condition that needs a deployed account to decide — an Access Analyzer finding, a Config evaluation — is `unchecked` when the review has only the diff. Say which detector would decide it.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the condition identifier where the rule and condition number go, and a correction that is an instruction: the resource or line, what to change, and to what.

Never quote an account ID, an ARN or a policy from the change into a finding beyond what the line already shows; a finding that repeats AWS detail into a pull-request comment is an exit too (`rules/exposure.md`).

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language defect in the code that calls AWS.** A swallowed exception, an unannotated surface, a leaked goroutine is the language skill's.

**Terraform as a language.** Module structure, state, providers and plans are the infrastructure-as-code plugin's; this skill reads only what the AWS resources declare.

**Application access control.** Whether a user of one tenant can reach another's record is `ahrena-engineering-security:reviewing-access`, even when the record lives in DynamoDB.

**A credential written as a literal.** That is `ahrena-engineering-security:reviewing-secrets`, which runs on every file. This skill reports where a credential is stored and how it is read, not the literal.

**Another cloud.** A change to Google Cloud or Azure resources is that vendor's plugin.
