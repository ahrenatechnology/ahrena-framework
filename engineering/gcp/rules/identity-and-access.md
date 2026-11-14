---
id: identity-and-access
type: rule
clade: engineering
subclade: gcp
title: Least-Privilege Identity on Google Cloud
statement: On Google Cloud: no basic role, no grant wider than the resource, no service account key where another identity serves, nothing public by default.
enforcement: judgment
references:
  - docs/identity-and-access.md
---

# Least-Privilege Identity on Google Cloud

A grant on Google Cloud gives a principal a role on a resource, and everything beneath that resource inherits it. Five conditions bound what a change may grant. Each names the vendor's detector, which reports the state on a deployed project, and the reviewer, who reads it in the change before it is deployed. [`docs/identity-and-access.md`](../docs/identity-and-access.md) cites the Google Cloud page behind each.

A grant here is any form that produces an allow-policy binding: a Terraform `google_*_iam_*` resource, a `gcloud ... add-iam-policy-binding`, a Config Connector `IAMPolicyMember`, a role granted in the console and recorded in a runbook.

## Conditions

1. **No basic role.** No change grants `roles/owner`, `roles/editor` or `roles/viewer` to any principal, and no workload runs as a default service account that holds Editor. A predefined or custom role that names the permissions the principal uses replaces it. Decided on the deployed project by the Security Command Center findings `PRIMITIVE_ROLES_USED`, `ADMIN_SERVICE_ACCOUNT` and `DEFAULT_SERVICE_ACCOUNT_USED`, prevented for default service accounts by the Organization Policy constraint `iam.automaticIamGrantsForDefaultServiceAccounts`, and decided in the change by a reviewer.

2. **The narrowest scope that serves.** A role is granted on the resource the principal acts on (the secret, the bucket, the topic, the service account), not on the project, folder or organization, unless the principal acts on every resource of that kind beneath it. The Service Account User and Service Account Token Creator roles are granted on one service account, never on the project. A role whose permissions the principal has not used is removed. Decided on the deployed project by the IAM role recommender and the finding `OVER_PRIVILEGED_SERVICE_ACCOUNT_USER`, inspected with Policy Analyzer, and decided in the change by a reviewer.

3. **One service account per workload.** Each application or job runs as a service account of its own, and no two workloads with different needs share one. Decided by a reviewer, with Policy Analyzer listing what a shared account reaches.

4. **No service account key where another identity serves.** No change creates, uploads, stores or distributes a service account key for a workload that runs on Google Cloud (it uses the attached service account), on GKE (Workload Identity Federation for GKE), or outside Google Cloud on a platform that issues OIDC or SAML tokens, CI included (Workload Identity Federation). A person acts as a service account by impersonation. A key that remains is named in the change with the reason no alternative serves. Prevented by the constraints `iam.disableServiceAccountKeyCreation` (or `iam.managed.disableServiceAccountKeyCreation`) and `iam.disableServiceAccountKeyUpload`, reported by `USER_MANAGED_SERVICE_ACCOUNT_KEY` and `SERVICE_ACCOUNT_KEY_NOT_ROTATED`, and decided in the change by a reviewer.

5. **Nothing public by default.** No change binds a role to `allUsers` or `allAuthenticatedUsers`, makes a bucket, dataset, key or service readable by them, or turns off Cloud Run's invoker check, unless the resource is meant to be read by anyone on the internet and the change says so. Prevented by `storage.publicAccessPrevention`, `storage.uniformBucketLevelAccess` and `iam.allowedPolicyMemberDomains`, reported by `PUBLIC_BUCKET_ACL`, `PUBLIC_DATASET`, `KMS_PUBLIC_KEY` and `NON_ORG_IAM_MEMBER`, and decided in the change by a reviewer.

## Where this stops

**A judgment rule, because the detectors that decide it run on a project and not on a change.** IAM Recommender, Policy Analyzer and Security Command Center read the deployed state; an Organization Policy constraint refuses a configuration at the API. None of them reads a pull request, and a grant can be written in Terraform, a shell script, a YAML manifest or a runbook, so no single parser sees every form. The reviewer is the gate in the change; the vendor's tools are the backstop after it, and an installation that has not enabled them has only the first.

**An organization policy is the stronger detector, and this plugin does not set it.** Which constraints an organization enforces is that client's decision, made in its installation (`ahrena-engineering-fundamentals:rules/client-logic.md`). A change that would need an override of an inherited constraint is a question for the organization's owner, not a finding against the change.

**Basic roles in a sandbox.** A personal or throwaway project with no production data is outside condition 1. The condition holds in every project that serves or stores anything a client relies on.

**The admin roles of the bootstrap.** The identity that creates the organization's structure holds broad roles by necessity. Condition 2 applies to it as to anyone else: the role sits on the narrowest node that serves, and is not held by a workload.

**Who an application's own users are** is the application's authorization, read by `ahrena-engineering-security:skills/reviewing-access/SKILL.md`, not by this rule.
