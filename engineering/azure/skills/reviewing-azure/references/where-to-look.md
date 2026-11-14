# Where each condition shows in a change

A lookup, not a restatement: the condition's text is in its rule. Property names are those of the Azure Resource Manager template reference (Bicep and ARM JSON share them), read on 2026-11-14 in the [template reference](https://learn.microsoft.com/en-us/azure/templates/). A Terraform `azurerm` configuration sets the same property through the provider argument its documentation maps to it; read the provider's documentation for the version the project pins, because argument names change between major versions.

## identity-and-access

| Condition | Resource type | What to read |
|---|---|---|
| 1 | `Microsoft.Authorization/roleAssignments` | `roleDefinitionId` (which role) and the top-level `scope` (which resource); an assignment with no `scope` applies at the deployment's scope, usually the resource group. Compare with the SDK calls the principal's code makes. |
| 1 | `Microsoft.Authorization/roleDefinitions` | `permissions[].actions` and `permissions[].dataActions` containing `*`; `assignableScopes` wider than the workload. |
| 2 | `Microsoft.Authorization/roleAssignments` | `roleDefinitionId` resolving to Owner (`8e3af657-a8ff-443c-a75c-2fe8c4bcb635`) or Contributor (`b24988ac-6180-42a0-ab88-20f7382dd24c`), or to another role under the built-in roles reference's *Privileged* heading, for any `principalType`. A `User` or `Group` assignment of one is also read under condition 5. |
| 3 | `Microsoft.Storage/storageAccounts` | `allowSharedKeyAccess` absent or `true` (null means permitted); `listKeys()` in a template or an output; a connection string with `AccountKey=` in an app setting. |
| 3 | `Microsoft.Web/sites`, `Microsoft.App/containerApps` | a top-level `identity` absent while the app reads a secret, key or password from settings to call an Azure service. |
| 3 | pipeline definitions | a client secret variable passed to `azure/login` or `az login --service-principal -p`, where a federated credential serves. |
| 4 | storage, Key Vault, SQL server, and any resource with `publicNetworkAccess` | `publicNetworkAccess` not `Disabled` on a data or secret store with no recorded caller; for storage `allowBlobPublicAccess: true`; `networkAcls.defaultAction: 'Allow'`. A private endpoint added beside `publicNetworkAccess: 'Enabled'` fails. |
| 4 | `Microsoft.Network/networkSecurityGroups` | `securityRules[].properties` with `direction: 'Inbound'`, `access: 'Allow'`, `sourceAddressPrefix` of `*` or `Internet`, on a management port (`22`, `3389`) or `*`. |
| 4 | `Microsoft.App/containerApps` | `configuration.ingress.external: true` on an app the design says is internal. |
| 5 | role assignments to `principalType: 'User'` with a privileged role | a standing assignment where PIM eligibility serves. |

## data-protection

| Condition | Resource type | What to read |
|---|---|---|
| 1 | `Microsoft.Storage/storageAccounts` | `minimumTlsVersion` absent, `TLS1_0` or `TLS1_1`. Absent fails, because an unset account accepts TLS 1.0. |
| 1 | `Microsoft.Sql/servers` | `minimalTlsVersion` set below `1.2` (note the spelling differs from storage). |
| 1 | `Microsoft.Web/sites` | `siteConfig.minTlsVersion` below `1.2`. |
| 2 | `Microsoft.Storage/storageAccounts` | `supportsHttpsTrafficOnly: false`. |
| 2 | `Microsoft.Web/sites` | `httpsOnly` absent or `false`; `siteConfig.ftpsState: 'AllAllowed'`. |
| 2 | `Microsoft.App/containerApps` | `configuration.ingress.allowInsecure: true`. |
| 3 | SQL databases | a transparent data encryption child resource with state `Disabled`. |
| 4 | `Microsoft.KeyVault/vaults` | `enablePurgeProtection` absent or `false` on a production vault; `enableRbacAuthorization` not `true` (set it explicitly, since the default depends on the API version); `accessPolicies` entries. |
| 5 | the design record | a requirement naming a customer-managed key, against the store's encryption settings. |

## exposure

| Condition | Code shape |
|---|---|
| 1 | a `catch`/`except` of `RequestFailedException` (.NET), `HttpResponseError` or another `azure.core.exceptions` type (Python), `RestError` (JavaScript), or the Go, Java equivalents, whose message, `GetRawResponse()`, `response`, `error`, `details` or string form reaches a response, a rendered page, a redirect or a CLI result. Also a resource id, subscription id or tenant id built into a response. |
| 2 | the same exception, a deployment's outputs, a credential or a client object handed whole to a logger, a span attribute or an exception tracker; the correction logs named fields: operation, status, error code, correlation id. |
| 3 | a tag value, a resource name or a template `output` holding a secret, a connection string, `listKeys()`, personal data, or a principal id meant to stay internal. |
| 4 | `ASPNETCORE_ENVIRONMENT=Development` or an equivalent debug flag in a production app setting or container environment. |
| 5 | a pipeline step running `az role assignment list`, `az account show`, `az ad sp show` or printing deployment outputs or what-if results to a log. |

## cost-attribution

| Condition | What to read |
|---|---|
| 1 | every new resource and resource group: a `tags` object with the project's owner tag, or an Azure Policy `modify` assignment in scope that adds it. |
| 2 | `Microsoft.Consumption/budgets` at the workload's scope: `amount`, and `notifications` whose entries have `contactEmails` or `contactGroups` (action groups); a budget with neither reaches nobody. Absence of any budget at the scope is the finding. |
| 3 | a non-production environment's resource group with no end date in a tag or the design record. |
