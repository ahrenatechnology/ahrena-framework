---
id: cloud-authentication
type: doc
clade: engineering
subclade: devops
title: Reaching AWS, Google Cloud and Azure from GitHub Actions by OIDC
summary: How a GitHub Actions job exchanges its OIDC token for short-lived credentials on AWS, Google Cloud and Azure, what each cloud must trust and how narrowly, which login action and inputs each uses, and where each cloud plugin takes over.
references:
  - rules/cloud-credentials.md
  - rules/protected-deployments.md
  - docs/environments-and-secrets.md
  - ahrena-engineering-aws:docs/identity-and-access.md
  - ahrena-engineering-gcp:docs/identity-and-access.md
  - ahrena-engineering-azure:docs/identity-and-access.md
---

# Reaching AWS, Google Cloud and Azure from GitHub Actions by OIDC

The companion to [`rules/cloud-credentials.md`](../rules/cloud-credentials.md). It covers the half of the federation that a pipeline author touches: the token GitHub issues, the claim each cloud should trust, and the workflow lines. What the cloud then lets the identity do, which role, which scope, belongs to the cloud plugin, and this page points at it instead of restating it.

## The token

Each job can request an OIDC token from GitHub's provider; the cloud validates it and issues "a short-lived access token that is only valid for a single job" ([OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect)). The job needs `id-token: write`: "Without `id-token: write`, the OIDC JWT ID token cannot be requested" ([OpenID Connect reference](https://docs.github.com/en/actions/reference/security/oidc)). The permission goes on the deploy job, not the workflow, so a test job cannot mint a cloud token ([`rules/token-permissions.md`](../rules/token-permissions.md)).

The claim that matters is `sub`. Its formats are fixed by the reference page: `repo:ORG/REPO:environment:NAME` when the job names an environment, `repo:ORG/REPO:ref:refs/heads/BRANCH` or `…:ref:refs/tags/TAG` otherwise, and `repo:ORG/REPO:pull_request` for a pull-request run with no environment. **A deploy job names its environment, and the cloud trusts the environment subject.** Then only a job that passed the environment's protection rules can assume the production identity, which is the property [`rules/protected-deployments.md`](../rules/protected-deployments.md) condition 5 asks for.

Two changes to the claim are recent. Repositories created after 15 July 2026 emit an immutable subject that carries the owner and repository IDs, not only their names ([OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect)); a trust condition written against the name alone fails for such a repository, as the `configure-aws-credentials` README warns. And the subject can be customised per repository through the REST API; the reference page says to create the matching cloud condition first, or tokens are rejected.

## AWS

GitHub's how-to registers `https://token.actions.githubusercontent.com` as an IAM OIDC provider with audience `sts.amazonaws.com`, then edits the role's trust policy "adding the `sub` field to the validation conditions" ([Configuring OpenID Connect in Amazon Web Services](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)). AWS now enforces that condition: IAM checks that `token.actions.githubusercontent.com:sub` "is present and that its value is not solely a wildcard character … or null", and refuses the policy otherwise; without it, "GitHub Actions from organizations or repositories outside of your control are able to assume roles" ([Create a role for OpenID Connect federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html)). The same page "strongly recommend[s]" protection rules on the environment a role trusts.

In the workflow: `aws-actions/configure-aws-credentials` with `role-to-assume` and `aws-region`, and no key inputs; its README calls OIDC "recommended because it provides temporary credentials" ([configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)). The current major is v6, pinned by SHA ([`rules/action-pinning.md`](../rules/action-pinning.md)).

What the role may do is the AWS plugin's: [`least-privilege.md`](../../aws/rules/least-privilege.md) for the policy, and [`identity-and-access.md`](../../aws/docs/identity-and-access.md) for why a role and not a key.

## Google Cloud

Google's guide creates a Workload Identity Pool and an OIDC provider for GitHub, maps "at minimum … `google.subject` to `assertion.sub`", and, for GitHub, requires an attribute condition: "you must use an attribute condition that restricts access to tokens issued by your GitHub organization" ([Configure Workload Identity Federation with deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)). The page recommends the numeric claims (`repository_id`, `repository_owner_id`) over names, which can be squatted, and recommends granting roles directly to the federated principal (`principal://` or `principalSet://`) over impersonating a service account, which remains for products with API limits. GitHub's own how-to says the same in its words: you "must define at least one condition" ([Configuring OpenID Connect in Google Cloud Platform](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-google-cloud-platform)).

In the workflow: `google-github-actions/auth` (major v3) with `workload_identity_provider`, and `service_account` only when impersonating; never `credentials_json`. Its README marks direct federation "Preferred" and says "Always add an Attribute Condition" ([google-github-actions/auth](https://github.com/google-github-actions/auth)).

What the principal may do is the Google Cloud plugin's: conditions 2 and 4 of [`identity-and-access.md`](../../gcp/rules/identity-and-access.md), and the table of what replaces a key in [`identity-and-access.md`](../../gcp/docs/identity-and-access.md).

## Azure

Microsoft's guide adds a federated identity credential to an Entra application or a user-assigned managed identity, and the workflow passes `client-id`, `tenant-id` and `subscription-id`, with audience `api://AzureADTokenExchange` by default ([Authenticate to Azure from GitHub Actions by OpenID Connect](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)). The credential's subject must "exactly match" the workflow's, and a mismatch "fails without error"; wildcards are not supported, and an application or identity holds at most 20 federated credentials ([Create a trust relationship with an external identity provider](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust)). Twenty is a design limit: one credential per environment of one repository fits; one per branch does not. The same page writes the pull-request subject as `pull-request` where GitHub's reference writes `pull_request`; copy the subject from the token, not from either page. Microsoft's guide also says that on a public repository the three identifiers go in environment secrets, so a job reads them only after approval.

In the workflow: `azure/login` with the three identifiers and no `creds`. The README "strongly encourage[s]" v3 and recommends "OIDC based authentication" ([Azure/login](https://github.com/Azure/login)); Microsoft's guide still shows v2.

What the identity may do is the Azure plugin's: conditions 1 to 3 of [`identity-and-access.md`](../../azure/rules/identity-and-access.md), and the credential order in [`identity-and-access.md`](../../azure/docs/identity-and-access.md).

## The same shape, three times

| | AWS | Google Cloud | Azure |
|---|---|---|---|
| Trusts | IAM OIDC provider, role trust policy | Workload Identity Pool and provider | Federated credential on an app or managed identity |
| Narrowed by | `sub` condition (enforced) | attribute condition (required) | exact subject (no wildcard) |
| Audience | `sts.amazonaws.com` | the provider's resource name (the action's default) | `api://AzureADTokenExchange` |
| Action, major | `aws-actions/configure-aws-credentials`, v6 | `google-github-actions/auth`, v3 | `azure/login`, v3 |
| Never | `aws-access-key-id` | `credentials_json` | `creds` |

## Where this stops

**Terraform's backend and providers** read the same credentials from the environment the login action sets; how the backend is configured is the Terraform plugin's [`state.md`](../../terraform/rules/state.md), and the cloud plugin's for the backend's own settings.

**A runner on the cloud's own compute** uses the identity it runs under, which is the cloud plugin's subject entirely.

**Custom claims and a customised subject** are covered only as far as the warning above; the reference page has the API.
