# Azure deployment error codes

Each row: what the code means, where to look, and what fixes it. Read on 2026-11-14 from Microsoft's troubleshooting pages; the page behind each row is linked in its last column. A code that is not here is looked up on [Troubleshoot common Azure deployment errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) before a theory is formed.

## Authorization and policy

| Code | Means | Look | Fix | Source |
|---|---|---|---|---|
| `AuthorizationFailed` | the deploying principal lacks the action at the scope; can also mean a required resource provider is not registered | the action and scope named in the message; the principal's role assignments at that scope | assign the narrowest role that grants the named action at the named scope; wait up to 10 minutes after a new assignment before retrying; never grant Owner or Contributor to clear it | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors), [Troubleshoot Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting) |
| `PrincipalNotFound` | the principal in a role assignment does not exist in the directory yet; usually a replication delay after creating it | whether the identity was created in the same deployment | set `principalType` (`ServicePrincipal`, `User`, `Group`) on the role assignment; for a new group, wait a few minutes | [Troubleshoot Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting) |
| `RoleAssignmentUpdateNotPermitted` | an existing assignment's principal, role or scope was changed | the assignment's `name` | give the assignment a deterministic name built with `guid()` from scope, principal and role, so a different binding is a different assignment | [Troubleshoot Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting) |
| `RequestDisallowedByPolicy` | an Azure Policy assignment denied the resource | the `policyAssignment` and `policyDefinition` in the error; the name is the last segment of each id | read the definition (`az policy definition show --name NAME`) and change the template to comply; an exemption is the policy owner's decision, not the deployer's | [Request disallowed by policy](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/error-policy-requestdisallowedbypolicy) |

## Subscription, region and capacity

| Code | Means | Look | Fix | Source |
|---|---|---|---|---|
| `MissingSubscriptionRegistration`, `NoRegisteredProviderFound` | the subscription is not registered for the resource provider, or the API version or location is not supported | `az provider list --query "[?namespace=='Microsoft.X']" --output table` | `az provider register --namespace Microsoft.X`; check supported locations and API versions with `az provider show` | [Resource provider registration errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/error-register-resource-provider) |
| `SkuNotAvailable` | the SKU is not offered in the chosen location | the SKU and location in the template | pick a SKU available in that location, or another location | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `OperationNotAllowed`, `ResourceQuotaExceeded` | the SKU does not allow the operation, or the deployment exceeds a subscription, resource group or region quota | the quota named in the message | stay within the quota or request an increase; an increase is the subscription owner's request | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `DeploymentQuotaExceeded` | the resource group holds 800 deployments in its history | `az deployment group list --resource-group RG --query "length(@)"`; a `CanNotDelete` lock on the group, an opt-out from automatic deletion, or many concurrent deployments | delete old history entries (`az deployment group delete`); deleting history does not touch deployed resources | [Deployment quota exceeded](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/deployment-quota-exceeded) |
| `SubscriptionRequestsThrottled` | Resource Manager is throttling the subscription (HTTP 429) | the `Retry-After` header | wait as long as it says and retry; reduce parallel deployments | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |

## Template and naming

| Code | Means | Look | Fix | Source |
|---|---|---|---|---|
| `DeploymentFailed` | a wrapper; the cause is in the details | the failed operations (step 2 of the skill) | act on the inner code | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `InvalidTemplate`, `InvalidTemplateDeployment` | template syntax or expression error | `bicep build`; the line the message names | fix the syntax | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `ResourceNotFound`, `InvalidResourceReference` | a referenced resource cannot be resolved | the `reference()` or `existing` parameters; whether the resource is in another group or subscription | correct the reference, or add a dependency so it is created first | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `ParentResourceNotFound` | a child resource was deployed before its parent | the parent's name and dependency | make sure the parent exists first | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `StorageAccountAlreadyTaken`, `StorageAccountAlreadyExists`, `AccountNameInvalid` | the storage account name is taken or breaks the naming rules | the name | use a unique, valid name | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `ReservedResourceName` | the name contains a reserved word | the name | rename | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `LocationRequired` | a resource has no location | the resource | give it a location | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |

## State and concurrency

| Code | Means | Look | Fix | Source |
|---|---|---|---|---|
| `Conflict` | the operation is not allowed in the resource's current state | the resource's state | change it in an order the resource allows | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `AnotherOperationInProgress`, `DeploymentActiveAndUneditable` | a concurrent operation or deployment holds the resource or group | the activity log | wait for it to finish | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `InUseSubnetCannotBeDeleted` | an update deletes and recreates a resource whose subnet is in use | the properties the template omitted | specify all unchanged values so the update does not recreate it | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |
| `DeploymentFailedCleanUp` | a complete-mode deployment could not delete resources outside the template | the principal's delete permission | deploy in incremental mode, or grant delete where complete mode is intended | [common errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) |

## Where the activity log helps, and where it does not

The activity log records control-plane operations such as deployment errors, usually within 3 to 20 minutes, and keeps them 90 days. It is not an authentication or authorization audit log: a request Resource Manager rejects before an operation starts leaves no entry ([Activity log](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/activity-log)). An `AuthorizationFailed` that never appears there is not a missing log; it is that case.
