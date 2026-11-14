---
id: identity-and-access
type: doc
clade: engineering
subclade: gcp
title: Identity and Access on Google Cloud
summary: How Google Cloud decides who may do what, why basic roles and service account keys are the two grants the vendor itself asks you to avoid, which identity replaces a key in each situation, and which of the vendor's tools reports each condition of the identity rule.
references:
  - rules/identity-and-access.md
  - docs/architecture-framework.md
---

# Identity and Access on Google Cloud

This is the companion to [`rules/identity-and-access.md`](../rules/identity-and-access.md). The rule states five conditions; this document explains the model they rest on, cites the Google Cloud page behind each one, and names the vendor's detector for each. Every page below was read on 2026-11-14; the documentation now lives under `docs.cloud.google.com`, to which `cloud.google.com/...` links redirect.

## How access is decided

Three kinds of policy meet at every request.

- **Allow policies** bind principals to roles on a resource. A role is a set of permissions. Allow, deny and organization policies are inherited down the resource hierarchy, so the effective policy on a resource is its own plus every ancestor's ([Resource hierarchy](https://docs.cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy)). A role granted on a project therefore reaches every resource in it, which is why the vendor asks for the narrowest scope that serves ([Use IAM securely](https://docs.cloud.google.com/iam/docs/using-iam-securely)).
- **Deny policies** remove permissions whatever the roles say; IAM checks the relevant deny policies before the allow policies ([Deny policies](https://docs.cloud.google.com/iam/docs/deny-overview)).
- **Organization policies** constrain how a resource may be configured, where IAM constrains who may act on it ([Organization Policy overview](https://docs.cloud.google.com/resource-manager/docs/organization-policy/overview)). This is the vendor's preventive control: a constraint refuses the configuration before it exists, where IAM Recommender or Security Command Center only report it afterwards.

IAM Conditions add attribute-based checks to a binding, written in CEL over the resource, the request and the principal ([IAM Conditions](https://docs.cloud.google.com/iam/docs/conditions-overview)). A conditional binding is how a grant expires on its own, which the vendor recommends for access that is temporary ([Use IAM securely](https://docs.cloud.google.com/iam/docs/using-iam-securely)).

## Basic roles

Owner, Editor and Viewer are the basic roles. The vendor calls them highly permissive and says not to grant them in production unless there is no alternative, using predefined or custom roles instead ([Roles overview](https://docs.cloud.google.com/iam/docs/roles-overview); [Use IAM securely](https://docs.cloud.google.com/iam/docs/using-iam-securely)). Owner is reserved for the case where nearly universal access is required.

The common way a basic role arrives without anyone granting it is the **default service account**. Some services create a default service account when they are enabled, and, depending on organization policy, it may be granted Editor on the project automatically. The vendor recommends enforcing `iam.automaticIamGrantsForDefaultServiceAccounts` and replacing an existing Editor grant with narrower roles, checking the effect first with Policy Simulator ([Service account types](https://docs.cloud.google.com/iam/docs/service-account-types); [Best practices for using service accounts](https://docs.cloud.google.com/iam/docs/best-practices-service-accounts)).

## Groups and dedicated service accounts

Roles go to groups rather than to individual users ([Use IAM securely](https://docs.cloud.google.com/iam/docs/using-iam-securely)). Each application gets its own service account, holding only what that application needs ([Best practices for using service accounts](https://docs.cloud.google.com/iam/docs/best-practices-service-accounts)). A shared service account makes every grant it needs a grant to every workload that runs as it.

The Service Account User role on a service account lets its holder act as that account, so it reaches everything the account reaches; the vendor asks that it be granted narrowly ([Use IAM securely](https://docs.cloud.google.com/iam/docs/using-iam-securely)). Security Command Center reports it granted at project level instead of on one service account as `OVER_PRIVILEGED_SERVICE_ACCOUNT_USER` ([Vulnerability findings](https://docs.cloud.google.com/security-command-center/docs/concepts-vulnerabilities-findings)).

## Keys, and what replaces them

A service account key is a long-lived credential. The vendor's position is to avoid keys whenever another option exists, because a key that is not managed carefully is a security risk: it can leak through a repository, a bucket, an email or a backup, and the account it unlocks faces no further sign-in check ([Best practices for managing service account keys](https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys); [Best practices for using service accounts](https://docs.cloud.google.com/iam/docs/best-practices-service-accounts)).

What replaces a key depends on where the code runs.

| Where the workload runs | What it uses instead of a key | Page |
|---|---|---|
| On Google Cloud (Cloud Run, Compute Engine, Cloud Build and the rest) | the service account attached to the resource | [Best practices for using service accounts](https://docs.cloud.google.com/iam/docs/best-practices-service-accounts) |
| On GKE | Workload Identity Federation for GKE, which the vendor names the recommended way in most cases | [Workload Identity Federation for GKE](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/workload-identity) |
| Outside Google Cloud: another cloud, on-premises, a CI platform such as GitHub or GitLab, any OIDC or SAML 2.0 provider | Workload Identity Federation | [Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation) |
| A person who needs to act as a service account | impersonation, which issues short-lived credentials of a few hours or less and records both identities in the audit log | [Service account impersonation](https://docs.cloud.google.com/iam/docs/service-account-impersonation) |

Where a key remains unavoidable, the vendor's practice is to rotate it, never commit it to source, and set the key-exposure response constraint to disable a key Google detects as leaked, with the caveat that detection is not guaranteed ([Best practices for managing service account keys](https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)).

The organization policies that close the door are `iam.disableServiceAccountKeyCreation` (managed form `iam.managed.disableServiceAccountKeyCreation`) and `iam.disableServiceAccountKeyUpload`, applied at the organization root and overridden per project only where there is no alternative ([Organization policy constraints](https://docs.cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints); [Best practices for managing service account keys](https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)).

## Public principals

`allUsers` is anyone on the internet, signed in or not. `allAuthenticatedUsers` is anyone signed in to a Google Account, personal accounts included, so it is not "our users" ([Principals overview](https://docs.cloud.google.com/iam/docs/principals-overview)). A binding to either is a public grant.

For Cloud Storage, public access prevention stops data being made public through IAM or ACLs; it is enforced across a project, folder or organization by `storage.publicAccessPrevention` ([Public access prevention](https://docs.cloud.google.com/storage/docs/public-access-prevention)). Uniform bucket-level access turns ACLs off so IAM is the only path, and is enforced by `storage.uniformBucketLevelAccess` ([Uniform bucket-level access](https://docs.cloud.google.com/storage/docs/uniform-bucket-level-access)). `iam.allowedPolicyMemberDomains` limits which domains' principals may be granted roles at all ([Restricting identities by domain](https://docs.cloud.google.com/resource-manager/docs/organization-policy/restricting-domains)).

## What a new organization already enforces

Organizations created on or after 3 May 2024 have a baseline of constraints enforced by default. The page lists seven, among them `iam.managed.disableServiceAccountKeyCreation`, `iam.disableServiceAccountKeyUpload`, `iam.automaticIamGrantsForDefaultServiceAccounts`, `iam.allowedPolicyMemberDomains` and `storage.uniformBucketLevelAccess` ([Manage baseline constraints](https://docs.cloud.google.com/resource-manager/docs/manage-baseline-constraints)). `storage.publicAccessPrevention`, `compute.vmExternalIpAccess` and `sql.restrictPublicIp` are not in that list, so an organization that wants them sets them. An older organization has none of them unless someone set them, and a project that overrides an inherited constraint is where the defaults are lost; reading the effective policy on the project, not the organization's, is what tells.

## The vendor's detectors

| Detector | What it reports | Page |
|---|---|---|
| IAM role recommender | a role with permissions the principal has not used, from at most the last 90 days of usage (for project-level recommendations, the minimum observation period defaults to 90 days and can be set to 30 or 60); never applied automatically | [Role recommendations](https://docs.cloud.google.com/policy-intelligence/docs/role-recommendations-overview) |
| Policy Analyzer | which principals have which access to which resources, across an organization, folder or project | [Policy Analyzer](https://docs.cloud.google.com/policy-intelligence/docs/policy-analyzer-overview) |
| Policy Troubleshooter, Activity Analyzer, service account insights, Policy Simulator | why a principal has or lacks a permission; when a service account or key last called an API; service accounts unused in 90 days; the effect of a policy change before it is made | [Policy Intelligence overview](https://docs.cloud.google.com/policy-intelligence/docs/overview) |
| Security Command Center, Security Health Analytics | `PRIMITIVE_ROLES_USED`, `ADMIN_SERVICE_ACCOUNT`, `USER_MANAGED_SERVICE_ACCOUNT_KEY`, `SERVICE_ACCOUNT_KEY_NOT_ROTATED` (older than 90 days), `OVER_PRIVILEGED_SERVICE_ACCOUNT_USER`, `DEFAULT_SERVICE_ACCOUNT_USED`, `FULL_API_ACCESS`, `NON_ORG_IAM_MEMBER`, `PUBLIC_BUCKET_ACL`, `BUCKET_POLICY_ONLY_DISABLED` | [Vulnerability findings](https://docs.cloud.google.com/security-command-center/docs/concepts-vulnerabilities-findings) |
| Organization Policy | the constraints above, which refuse the configuration instead of reporting it | [Organization policy constraints](https://docs.cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints) |
| Cloud Audit Logs | changes to allow policies | [Use IAM securely](https://docs.cloud.google.com/iam/docs/using-iam-securely) |

The 90 days in the recommender and in `SERVICE_ACCOUNT_KEY_NOT_ROTATED` are the vendor's figures, attributed to the pages above; the rule adds no number of its own.

## Where this stops

This document covers the identities and grants of workloads and people on Google Cloud. It does not cover how an application authenticates its own end users (Identity Platform, see [`docs/services.md`](services.md)), and it does not lay out an organization's folders, groups or projects: that structure belongs to each client's installation, not to the platform (`ahrena-engineering-fundamentals:rules/client-logic.md`). Network-level access, which decides whether a request can reach a resource at all, is [`docs/networking.md`](networking.md).
