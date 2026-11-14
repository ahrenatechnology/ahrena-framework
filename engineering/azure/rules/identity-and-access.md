---
id: identity-and-access
type: rule
clade: engineering
subclade: cloud
title: Identity and access on Azure
statement: An Azure workload gets the narrowest role at the narrowest scope; no Owner or Contributor where a job role serves, no secret where a managed identity serves.
enforcement: judgment
references:
  - docs/identity-and-access.md
  - docs/networking.md
---

# Identity and access on Azure

Who can do what to which Azure resource, and with what credential. Five conditions, each a state a reader can find in a Bicep or ARM file, a Terraform `azurerm` configuration, a pipeline definition or the role assignments of a subscription, and each naming what decides it. [`docs/identity-and-access.md`](../docs/identity-and-access.md) carries the reasons and the Microsoft pages behind every condition; this file states the conditions and stops.

Three terms, in the sense Azure RBAC gives them. A **role assignment** binds a security principal (a user, a group, a service principal or a managed identity) to a role definition at a scope. A **scope** is a management group, a subscription, a resource group or a single resource, and an assignment at one is inherited by everything below it. A **privileged administrator role** is one the built-in roles reference lists under its *Privileged* heading: Owner, Contributor, User Access Administrator, Role Based Access Control Administrator and Reservations Administrator.

## Conditions

1. **A workload's role assignment is the narrowest built-in or custom role that grants what the workload calls, at the narrowest scope that holds what it touches.** A service that reads one storage account's blobs holds a blob data role on that account, not a role on its resource group or subscription. The state that fails is an assignment whose role grants actions the workload never calls, or whose scope contains resources the workload never touches. A custom role that names `*` in `Actions` or `DataActions` fails unless the definition records why the set cannot be listed. Decided in a change by a reviewer reading the assignment against the calls the code makes; in a running subscription by the Microsoft Defender for Cloud recommendation *Azure overprovisioned identities should have only the necessary permissions*, and by an Entra access review of Azure resource roles.

2. **No privileged administrator role is assigned where a job-function role serves.** Owner and Contributor are never assigned to a workload identity, a pipeline or a group of developers in order to "make it work". The state that fails is a privileged administrator role on a service principal, a managed identity or a standing user assignment, without a recorded reason that names the action no job-function role grants. A subscription has at most three Owners and more than one. Decided in a change by a reviewer; in a running subscription by the Defender for Cloud recommendations *Service Principals should not be assigned with administrative roles at the subscription and resource group level*, *Privileged roles should not have permanent access at the subscription and resource group level*, *A maximum of 3 owners should be designated for subscriptions* and *There should be more than one owner assigned to subscriptions*.

3. **No long-lived secret authenticates a workload where a managed identity or a federated credential serves.** A workload running on an Azure service that supports managed identities authenticates with one. A workload running outside Azure that has a token issuer Entra can trust (GitHub Actions, a Kubernetes cluster, another cloud) authenticates with workload identity federation. The states that fail are: a client secret on an app registration used by such a workload; a storage account key, a Shared Key connection string or a SAS token signed with an account key in code, configuration or a pipeline variable where Entra authorization serves; and a storage account whose `allowSharedKeyAccess` is not `false` when nothing on it needs Shared Key. Where neither a managed identity nor federation is possible, the credential is a certificate, not a password. Decided by a reviewer, and in a running subscription by the Azure Policy definitions *Storage accounts should prevent shared key access* and *App Service apps should use managed identity*. Secret lifetimes on app registrations are bounded by an Entra application management policy, where the tenant has one.

4. **Nothing is reachable from the public internet unless the design says it must be.** The data and control services a workload uses (storage, databases, Key Vault, a message broker, a container registry) set public network access to disabled and are reached through a private endpoint, unless the design records the caller that requires public reach. A private endpoint does not by itself close the public endpoint, so both are checked. The states that fail are: public network access enabled on a data or secret store with no recorded caller that needs it; a blob container or account that allows anonymous read access; an NSG rule that admits `Internet` or `*` to a management port. Decided by a reviewer; in a running subscription by the Defender for Cloud recommendations *Management ports should be closed on your virtual machines* and *Internet-facing virtual machines should be protected with network security groups*, and by built-in Azure Policy definitions such as *Storage accounts should disable public network access*, *Storage account public access should be disallowed*, *Azure Key Vault should disable public network access* and *Public network access on Azure SQL Database should be disabled*. [`docs/networking.md`](../docs/networking.md) says which service is public by default.

5. **Access is reviewed, and standing privileged access is avoided.** A human's privileged role on a production subscription is eligible through Privileged Identity Management and activated just in time, not permanently assigned. Role assignments on production subscriptions are reviewed on a recurring schedule the project records. The states that fail are a permanent privileged assignment to a user, and a production subscription with no recorded review. Decided by Microsoft Entra access reviews of Azure resource roles where the tenant is licensed for them, and by Defender for Cloud's *Permissions of inactive identities in your Azure subscription should be revoked*; otherwise by a reviewer reading the assignment list against the project's record.

## Where this stops

**The tenant and the subscription layout are the client's.** Which management groups exist, who the Owners are by name, which groups are created and which tenant hosts the workload are an installation's declaration, not this rule's content, by [`client-logic.md`](../../fundamentals/rules/client-logic.md). This rule checks the shape of an assignment and never names a principal.

**A detector named here runs in the client's tenant.** Defender for Cloud, Azure Policy and access reviews report on a subscription that has them enabled and, for access reviews, licensed. Where a project has none of them, every condition falls to the reviewer, and the review says which detector was missing.

**Microsoft Entra directory roles are not covered.** Global Administrator and the other Entra roles govern the directory, not Azure resources; their governance is the tenant administrator's, not a workload's.

**Condition 4 does not forbid a public endpoint.** A public web front end, a public API behind a gateway and a webhook receiver are public on purpose. The condition asks that the design say so; the protection of that endpoint is [`docs/networking.md`](../docs/networking.md).

**A role assigned for a migration or an incident is still an assignment.** It is held to the same conditions, and the record of why it exists is what lets the next review remove it.
