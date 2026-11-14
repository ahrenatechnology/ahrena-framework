---
id: identity-and-access
type: doc
clade: engineering
subclade: cloud
title: Identity and access on Azure, explained
summary: How Azure RBAC binds a principal to a role at a scope, which roles Microsoft marks privileged, why a workload authenticates with a managed identity or a federated credential instead of a secret, how access is reviewed, and what an Azure authorization error gives away.
references:
  - rules/identity-and-access.md
  - rules/exposure.md
---

# Identity and access on Azure, explained

The companion of [`rules/identity-and-access.md`](../rules/identity-and-access.md), and of the identity half of [`rules/exposure.md`](../rules/exposure.md). The rules state conditions; this says where each comes from, with the Microsoft page that says it. Every page cited here was read on 2026-11-14.

## The model: a principal, a role, a scope

An Azure RBAC role assignment binds a security principal to a role definition at a scope, and the assignment is inherited by every scope below it. That inheritance is why condition 1 of the rule asks for the narrowest scope as well as the narrowest role: a reader role on a subscription is a reader role on every resource group and resource in it.

Microsoft's own best-practice page says it directly: grant users the least privilege they need to get their work done, and avoid broader roles at broader scopes even when they seem more convenient at first ([Best practices for Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/best-practices)). The same page asks that roles be assigned to groups rather than directly to users, and that a custom role list its `Actions` and `DataActions` explicitly instead of using the `*` wildcard. The Well-Architected Framework's identity guidance (SE:05) puts the same idea in one line: an identity must not be allowed to do more than it needs to do ([Architecture strategies for identity and access management](https://learn.microsoft.com/en-us/azure/well-architected/security/identity-access)). The Microsoft cloud security benchmark carries it as PA-7, *Follow just enough administration (least privilege) principle* ([MCSB: Privileged Access](https://learn.microsoft.com/en-us/security/benchmark/azure/mcsb-privileged-access)).

## Privileged roles, and why Owner and Contributor are not defaults

The built-in roles reference has a *Privileged* heading, and it lists Contributor, Owner, Reservations Administrator, Role Based Access Control Administrator and User Access Administrator ([Azure built-in roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)). Owner grants full access to manage all resources *and* to assign roles; Contributor grants full access to manage all resources without assigning roles. Either one on a workload means a compromise of that workload can change or delete everything in scope, and Owner means it can also grant itself, or anyone, more.

The best-practice page asks to avoid a privileged administrator role when a job-function role can be used instead, to remove unnecessary privileged assignments, and to keep a maximum of three subscription owners to reduce the potential for breach by a compromised owner ([Best practices for Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/best-practices)). Defender for Cloud turns those into recommendations, which is where condition 2's detectors come from: *A maximum of 3 owners should be designated for subscriptions*, *There should be more than one owner assigned to subscriptions*, *Service Principals should not be assigned with administrative roles at the subscription and resource group level* and *Privileged roles should not have permanent access at the subscription and resource group level* ([Identity and access recommendations](https://learn.microsoft.com/en-us/azure/defender-for-cloud/recommendations-reference-identity-access)). The same reference has *Azure overprovisioned identities should have only the necessary permissions*, which is the running-subscription detector for condition 1.

"More than one" is there for the same reason as "at most three": a subscription whose only Owner leaves cannot be administered.

## Workload credentials: managed identity first, federation second, certificate last

A secret held by a workload is a secret that can leak and that expires. Microsoft states the order of preference for an application's credential on the app-registration best-practice page: use a managed identity whenever possible; where neither a managed identity nor another secure external identity provider is possible, use a certificate; and do not use password credentials, also called secrets ([Security best practices for application properties](https://learn.microsoft.com/en-us/entra/identity-platform/security-best-practices-for-app-registration)). The same page points at application management policies as the way to limit secret lifetimes or block secrets altogether.

**Managed identities** replace secrets such as access keys or passwords, and there are no credentials to manage ([Managed identities for Azure resources](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview)). A system-assigned identity is created with its resource and deleted with it; a user-assigned identity is a resource of its own, with an independent lifecycle, shareable across resources, and the page calls it the recommended type for Microsoft services. A user-assigned identity is the usual choice when several resources of one workload share an identity or when the role assignments must exist before the compute is created.

**Workload identity federation** is for code that runs outside Azure. It lets an Entra application or user-assigned managed identity trust tokens from an external issuer (GitHub Actions, any Kubernetes cluster, Google Cloud, AWS, SPIFFE, Azure Pipelines service connections), and the page names the problem it removes: secrets and certificates have to be stored and rotated, and service goes down when they expire ([Workload identity federation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation)). A deployment pipeline is the commonest case: it should hold no client secret at all.

The benchmark's IM-3, *Manage application identities securely and automatically*, asks for managed application identities instead of human accounts for applications ([MCSB: Identity Management](https://learn.microsoft.com/en-us/security/benchmark/azure/mcsb-identity-management)). The Well-Architected secrets guidance (SE:09) names managed identities as the way to eliminate stored credentials, and says not to hard-code secrets in code, configuration or pipelines ([Protecting application secrets](https://learn.microsoft.com/en-us/azure/well-architected/security/application-secrets)).

**Storage account keys are the case that gets missed.** A storage account accepts Shared Key authorization unless `AllowSharedKeyAccess` is set to `false`, and the property is unset by default. Microsoft recommends Entra ID over Shared Key, and ships the policy *Storage accounts should prevent shared key access* ([Prevent authorization with Shared Key](https://learn.microsoft.com/en-us/azure/storage/common/shared-key-authorization-prevent)). An account key is a credential to the whole account, with no identity attached to its use.

## Key Vault access

Key Vault is reached with Azure RBAC, not with legacy access policies: Microsoft's Key Vault security page says to use Azure RBAC, not to use legacy access policies, and that those have known security weaknesses and no Privileged Identity Management support ([Secure your Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault)). Since API version 2026-02-01, Azure RBAC is the default model for newly created vaults; switching an existing vault invalidates its access-policy permissions and causes an outage if the equivalent roles are not assigned first ([Azure RBAC for Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide)). The same pages recommend a vault per application, region and environment, which keeps a role on one vault from reaching another application's secrets.

## Standing access, just-in-time access and reviews

Privileged Identity Management provides just-in-time privileged access to Microsoft Entra ID and Azure resources ([What is Privileged Identity Management?](https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-management/pim-configure)). The benchmark's PA-2 is *Avoid standing access for user accounts and permissions*, and PA-4 is *Review and reconcile user access regularly* ([MCSB: Privileged Access](https://learn.microsoft.com/en-us/security/benchmark/azure/mcsb-privileged-access)).

Access reviews are the Entra feature for PA-4: they cover group membership, enterprise application access, Entra roles and, through PIM, Azure resource roles. They require Microsoft Entra ID Governance or Microsoft Entra Suite, with some capabilities available on Entra ID P2 ([What are access reviews?](https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview)). That licence is why condition 5 of the rule falls back to a reviewer: a tenant that has not bought it cannot run the detector.

## How long a change takes, and why that matters for diagnosis

A role assignment or removal can take up to 10 minutes to take effect, and a change to a managed identity's group or role membership can take several hours ([Troubleshoot Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting)). A deployment that assigns a role and immediately uses it can therefore fail with an authorization error that is gone on retry; the diagnosis skill treats that case before it treats the assignment as wrong. The same page documents `PrincipalNotFound` for a role assigned to a principal created seconds earlier, a replication delay fixed by setting `principalType` on the assignment.

## What an authorization error gives away

The Azure RBAC troubleshooting page prints the errors a refused call returns. The `AuthorizationFailed` message names the client and its object id, the action it attempted and the scope it attempted it over; a refused role-assignment write names the action `Microsoft.Authorization/roleAssignments/write` over a scope of the form `/subscriptions/{subscriptionId}/Microsoft.Authorization/roleAssignments/{roleAssignmentId}` ([Troubleshoot Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting)).

Each of those fields is useful to the operator and useful to an outsider: the object id says which identity the workload runs as, the action says what it is not allowed to do, and the scope says which subscription and resource it was reaching. That is why [`rules/exposure.md`](../rules/exposure.md) lists them and why its conditions translate the error before it crosses to a caller. The Azure SDKs carry the whole response on the exception: .NET's `RequestFailedException` exposes `Status`, `ErrorCode` and the raw response through `GetRawResponse()` ([RequestFailedException](https://learn.microsoft.com/en-us/dotnet/api/azure.requestfailedexception)); Python's `HttpResponseError` carries `status_code`, `reason`, the `response` and a formatted `error` ([HttpResponseError](https://learn.microsoft.com/en-us/python/api/azure-core/azure.core.exceptions.httpresponseerror)); JavaScript's `RestError` carries `code`, `statusCode`, the request and the response ([RestError](https://learn.microsoft.com/en-us/javascript/api/@azure/core-rest-pipeline/resterror)). The status and the error code are what an internal log needs; the rest stays inside.

## Where this stops

The tenant's own structure (which management groups, which groups, which people) is not here: it is the client's, by `ahrena-engineering-fundamentals`' client-logic rule. Entra ID directory roles, Conditional Access policy design and customer identity (Microsoft Entra External ID, see [`services.md`](services.md)) are not covered. Network reachability, the other half of "nothing public by default", is [`networking.md`](networking.md).
