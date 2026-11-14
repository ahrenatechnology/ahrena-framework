---
name: diagnosing-azure-deployments
description: Use when a deployment to Azure failed or the deployed workload does not come up - a Bicep or ARM deployment that stopped with an error code (AuthorizationFailed, RequestDisallowedByPolicy, MissingSubscriptionRegistration, SkuNotAvailable, a quota, PrincipalNotFound, DeploymentQuotaExceeded), a Container Apps revision that will not activate, an App Service app that will not start. Finds the stage that failed, reads the real error code, names the cause from Microsoft's troubleshooting pages, proposes the fix and a check, and reports without copying Azure identifiers anywhere a client can read.
type: skill
clade: engineering
subclade: cloud
references:
  - rules/identity-and-access.md
  - rules/exposure.md
  - docs/identity-and-access.md
  - docs/networking.md
---

# Diagnosing Azure deployments

A failed deployment hands back a code, and the outer one is not the one to act on: `DeploymentFailed` is a wrapper whose details hold the error that matters. This skill gets to that error, matches it against Microsoft's troubleshooting pages, and fixes the cause rather than the symptom. The table of codes is `references/error-codes.md`.

## 1. Name the stage that failed

Microsoft distinguishes three kinds of failure ([Find error codes](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/find-error-code)), and a fourth comes after the deployment succeeds:

- **validation**: the file does not parse or a template expression is wrong, before anything is sent;
- **preflight**: Resource Manager rejected the request before deploying anything;
- **deployment**: a resource failed while being created or updated;
- **runtime**: every resource deployed and the application does not start or answer.

Validation and preflight errors appear in the activity log and not in the deployment history, so a deployment that "has no history" failed before it started. Write down the stage; every later step depends on it.

## 2. Read the real error code

For a validation or preflight failure, re-run validation and read its output.

```sh
bicep build main.bicep
az deployment group validate --resource-group RG --template-file main.bicep
```

For a deployment failure, list the operations and read the failed ones.

```sh
az deployment group show --resource-group RG --name DEPLOYMENT
az deployment operation group list --resource-group RG --name DEPLOYMENT --query "[*].properties"
```

Use `az deployment sub`, `mg` or `tenant` for the other scopes. The code to act on is the innermost one in the failed operation's `statusMessage`, not `DeploymentFailed`. The portal shows the same under the resource group's *Deployments* and *Activity log*.

## 3. Match the code

Open `references/error-codes.md` and find the code. Each row says what it means, where to look, and what fixes it, with the Microsoft page it comes from. If the code is not in the table, read Microsoft's [common deployment errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) page for it before forming a theory.

## 4. Rule out timing before blaming configuration

Three failures go away on retry and are misdiagnosed as wrong configuration:

- a role assigned in the same deployment and used at once: role assignments can take up to 10 minutes to take effect, and a managed identity's group membership several hours;
- `PrincipalNotFound` on a principal created seconds earlier: a replication delay, fixed by setting `principalType` on the role assignment;
- `AnotherOperationInProgress` or `DeploymentActiveAndUneditable`: a concurrent operation on the same resource or group.

`docs/identity-and-access.md`, section *How long a change takes*, has the source. If the failure matches one of these, the fix is `principalType` or a wait, not a broader role. Granting Owner or Contributor to make an authorization error disappear breaks `rules/identity-and-access.md` condition 2, and it is the fix this skill must not propose.

## 5. Diagnose a runtime failure

When the deployment succeeded and the workload did not:

- **Container Apps.** Microsoft's troubleshooting table maps each symptom to a first check: a new revision that fails to deploy, to whether the image can be pulled; a revision stuck provisioning, or degraded with *0/1 replicas ready*, to the health probes; a request that fails, to the ingress, whose target port must be the port the container listens on. Read the log stream with *Console* or *System* logs selected, and *Diagnose and solve problems* ([Troubleshooting in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/troubleshooting)).
- **App Service.** Open *Diagnose and solve problems*, which covers availability, configuration and deployment without setup and is most useful for problems in the last 24 hours ([App Service diagnostics](https://learn.microsoft.com/en-us/azure/app-service/overview-diagnostics)). An ASP.NET Core app that cannot start returns *502.5 Process Failure* ([Handle errors in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/error-handling)).
- **Private networking.** An app that cannot reach a store after its public access was disabled may still be resolving the store's public name: check the private endpoint's private DNS zone and its link to the virtual network (`docs/networking.md`).

Do not turn on a framework's detailed-error page in production to see the error; read the platform logs instead (`rules/exposure.md`, condition 4).

## 6. Fix, preview, and verify

Change the template, not the resource by hand, so the next deployment does not undo the fix. Preview the change before deploying it.

```sh
az deployment group what-if --resource-group RG --template-file main.bicep
```

What-if reports changes and makes none. Its output can carry noise: a property the template omits but the platform sets may show as deleted, and it does not evaluate `newGuid()`, `utcNow()`, secure parameters or `listKeys()` ([Bicep what-if](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-what-if)). Deploy, and verify by the check the failure named: the operation succeeds, the revision is healthy, the endpoint answers.

## 7. Report without leaking

Write the diagnosis as: stage, error code, cause, fix, and the check that shows it worked. Name resources by their role in the design (`the orders storage account`), not by resource id.

Never paste into an issue, a pull request, a chat or any place a client can read: the raw error message, a subscription or tenant id, a principal's object id, a resource id, a role assignment list or a deployment's outputs. Those are the items of `rules/exposure.md`, and an error message from Azure Resource Manager carries most of them. The operator reads them in the portal or the CLI; the report carries the code and the cause.

## When this skill does not apply

**A design question before anything is deployed.** That is `designing-on-azure`.

**A change to review.** That is `reviewing-azure`, even when the change fixes a failure.

**A defect in the application's own logic** that is not about Azure: the language plugin's diagnosis skill.

**An Azure platform incident.** If Azure Service Health reports an incident in the region, the diagnosis is the incident; this skill does not work around it.
