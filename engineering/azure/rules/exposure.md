---
id: exposure
type: rule
clade: engineering
subclade: cloud
title: No Azure identity or layout leaves the workload
statement: No role assignment, subscription or tenant id, resource id, network layout or Azure SDK error text reaches an output, a log or an error a caller sees.
enforcement: judgment
references:
  - docs/identity-and-access.md
  - docs/networking.md
---

# No Azure identity or layout leaves the workload

The Azure form of the security plugin's exposure rule, [`layer-exposure.md`](../../security/rules/layer-exposure.md): nothing sensitive leaves the layer that owns it, and what a layer emits is an allowlist of named fields. That rule is vendor-agnostic and covers the general case, with a hook for the parts a script decides; this one names what is sensitive *on Azure* and where an Azure workload lets it out, so a builder and a reviewer recognise it in Azure terms.

The failure it exists for is concrete. An Azure Resource Manager authorization error carries the object id of the principal that was refused, the action it attempted and the scope it attempted it on, as a resource path that begins `/subscriptions/` and the subscription's id; the Azure RBAC troubleshooting page prints the template. A handler that returns that error to its caller has told the caller who the workload runs as, what it may not do, and where the resource lives. [`docs/identity-and-access.md`](../docs/identity-and-access.md) works the example through.

## What is sensitive here

A closed list. Each item is sensitive whatever its value happens to be today. A role and a scope described in words in a design or a review finding (`Storage Blob Data Reader on the orders account`), and a custom role's actions written in a design record or a template, are not an item there; an assignment as Azure records it, with its ids, is, and so is any of them in an application's output.

- **An identity:** a tenant id, a subscription id, a management group id, the object id, client id or application id of a user, group, service principal or managed identity.
- **An authorization:** a role assignment, a role definition, a custom role's action list, an Azure Policy assignment or definition id, a Key Vault access policy, a PIM eligibility.
- **A location:** a resource id (`/subscriptions/…/resourceGroups/…/providers/…`), a resource group name, a Key Vault or storage account endpoint that locates a store holding someone's data, a deployment name or a deployment's outputs.
- **A layout:** a virtual network or subnet address range, a private endpoint's IP address, a private DNS zone record, an internal host name, an NSG rule, a firewall rule.
- **An Azure error as it came:** the message, the raw response, the error body or the headers of an exception an Azure SDK raised (`RequestFailedException` in .NET, `HttpResponseError` in Python, `RestError` in JavaScript, and their equivalents in the other Azure SDKs), and the output of a failed `az` or deployment command.

## Conditions

1. **No application response, rendered page, CLI or tool result carries an item of the list above.** An endpoint that fails on an Azure call answers its caller with a generic message, a status the caller can act on and a correlation identifier, and nothing taken from the Azure error. The state that fails is a response body, a header, a redirect URL or an error page built from an Azure exception's message, its raw response or a field of it, or from a resource id, a subscription id or a role assignment. Decided by the security plugin's `hooks/check-exposure.py` where a caught error or an upstream response reaches the exit whole (its conditions 1 and 2), and by a reviewer reading each error path of the changed handlers for the rest: a field taken from the error, or an identifier built into the response.

2. **No log, trace attribute or metric label carries an item of the list above, whole or as a field.** What is logged on an Azure failure is a set of named fields: the operation, the HTTP status, the service's error code (the `ErrorCode` or `error.code` the SDK exposes), and the correlation identifier the caller was given. Two states fail: a logging call handed the exception object, its message, its raw response, a deployment's outputs, or a whole client or credential object, because each of those carries an item of the list and the logger serialises it whole; and a named field whose value is an item of the list, such as a subscription id, an object id, a resource id or a role assignment. The Well-Architected monitoring guidance asks that sensitive system information be scrubbed before logging. Decided by the security plugin's `hooks/check-exposure.py` for a whole exception or response handed to a logger, and by a reviewer for a named field whose value is an item of the list.

3. **No tag, resource name or deployment output carries a secret or a sensitive value.** Tags are stored as plain text and readable by anyone with read access to the resource. The state that fails is a tag value, a resource name or a template output that holds a credential, a connection string, personal data, or an item of the list above that the reader of that resource should not have. Decided by a reviewer reading the template.

4. **No developer error page is reachable outside a development environment.** ASP.NET Core's documentation ([Handle errors in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/error-handling)) says not to enable the Developer Exception Page unless the app runs in the Development environment, and not to share detailed exception information publicly in production; the same holds for any framework's detailed-error or debug mode. The state that fails is a production deployment, an App Service app setting or a Container Apps environment variable that turns one on. Decided by a reviewer reading the deployment configuration.

5. **A pipeline or deployment log does not print an item of the list as a side effect.** A step that runs `az role assignment list`, `az account show`, prints a deployment's outputs or echoes a whole what-if result into a pipeline or deployment log fails, whoever can read that log today. A pipeline that previews with what-if reduces the result (its `--no-pretty-print` form is machine-readable; [Bicep what-if](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-what-if)) to a count of changes by type before anything is printed. Decided by a reviewer reading the pipeline definition.

## Where this stops

**An identifier inside the workload's own configuration is not an exit.** A resource id in a Bicep file or an environment variable the platform injects is where the identifier lives. A log is never inside that boundary, whoever can read it today: conditions 2 and 5 hold for every log, trace and metric, because who reads a log store changes without the code changing.

**The operator's own diagnosis is not a violation.** Reading a full deployment error in the portal or in `az deployment operation group list` is how a failure is diagnosed. Copying it into an issue, a pull request comment or a chat message that a client can read is an exit, and the diagnosis skill of this plugin writes its report without those items.

**A subscription id is not a credential, and the rule does not claim it is.** It is on the list because, with a role name and a resource path, it lets an outsider map the deployment, which is the failure in issue #294. Keeping it in is cheap; taking it back is not possible.

**The detector for the general case is not here.** The dependency-free hook that reports a whole error or upstream response written to an exit is the security plugin's `hooks/check-exposure.py`, under its exposure rule. This rule adds the Azure names a reader needs and ships no hook of its own; what that hook does not decide here is a reviewer's.
