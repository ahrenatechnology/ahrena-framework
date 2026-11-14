---
name: reviewing-azure
description: Use when a change under review edits Azure infrastructure (a Bicep or ARM template, a Terraform azurerm configuration, a pipeline that deploys to Azure) or application code that calls an Azure SDK, and the question is what an Azure reader would catch - a role broader than the calls need, Owner or Contributor on a workload, a client secret where a managed identity serves, a store left public, a TLS floor below 1.2, an Azure error or identifier reaching a caller or a log, a resource with no owner tag or budget. Reads the routed files against this plugin's four rules; every finding names the rule and the condition.
type: skill
clade: engineering
subclade: cloud
references:
  - rules/identity-and-access.md
  - rules/data-protection.md
  - rules/exposure.md
  - rules/cost-attribution.md
  - docs/identity-and-access.md
  - docs/networking.md
  - ahrena-engineering-quality:docs/review-findings.md
---

# Reviewing Azure

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has read the change against the rules that hold everywhere, and a language skill has read the code as code. This skill reads what needs an Azure reader. The conditions are the four rules of this plugin, cited as `identity-and-access/2`, `exposure/1` and so on; this skill does not restate them. Severity follows `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fires `azure-bicep` on Bicep and Bicep parameters files, `azure-iac` on ARM templates and Terraform files that use `azurerm`, `azure-pipeline` on a pipeline whose added lines sign in to Azure or run `az`, and `azure-sdk` on application code whose added lines touch an Azure SDK; the routes are in this plugin's `review-routes.json`, and `hooks/test-review-routes.py` checks each one. Those are the files this skill reads.

Before reading a line, find out what the project already decides: the infrastructure-as-code tool, whether the pipeline runs a policy check or `what-if`, the design record if `designing-on-azure` produced one, and which Azure Policy assignments and Defender for Cloud plans the project says are on. A condition a tenant detector already enforces with `deny` is still reported when the change violates it: the review is the earlier gate, and the deployment would only fail later on the same condition.

## 2. Open the rules and the lookup table

Open each of the four rules whose subject the change touches, and `references/where-to-look.md`, which says, for each condition, which property, resource type or code shape to read in Bicep, ARM, Terraform and SDK code.

| The change touches | Rule |
|---|---|
| a role assignment, a role definition, an identity, a credential, a connection string, public network access, an NSG | `rules/identity-and-access.md` |
| a storage account, a database, a Key Vault, a TLS or HTTPS setting, encryption settings | `rules/data-protection.md` |
| application code calling an Azure SDK, an error handler, a logging call, a tag, a template output, a pipeline step | `rules/exposure.md` |
| any new resource or resource group, a budget, an environment | `rules/cost-attribution.md` |

## 3. Read beyond the hunk

A role assignment is judged against the calls the code makes, so open the code that uses the identity. A private endpoint is judged with the public network access of the service it points at, which may be in another file. An SDK call is judged at the handler that catches its exception, which may be several frames up. Read the base revision of a line before calling it wrong.

## 4. Apply the conditions

Work rule by rule, condition by condition. Give the scenario in Azure terms: the resource, the property and its value, the principal and its role at its scope, or the path from the SDK exception to the response. `docs/identity-and-access.md` and `docs/networking.md` hold the defaults a template inherits when it omits a property; a missing property is a finding only when its default is the unsafe value.

For `exposure/1` and `exposure/2`, follow every `catch` or `except` of an Azure SDK exception in the change to where its value goes. An exception handed whole to a logger, or its message put in a response, is `blocking`. This is the condition the incident behind issue #294 would have met.

A condition whose answer depends on something only the client holds (whether a public endpoint is intended, which data needs a customer-managed key, who the budget's recipient is) is a `question`, naming who answers it. A state the template decides is not a question: a budget with no `notifications` at all reaches nobody and is `blocking`, whoever the recipient will be.

## 5. Write the findings

Each finding carries the fields in `ahrena-engineering-quality:docs/review-findings.md`: file and line, the rule and condition (`exposure/2`), the state observed, and a correction that is an instruction ("assign `Storage Blob Data Reader` on the account instead of `Contributor` on the resource group"). Never quote a real subscription id, tenant id, object id or secret in a finding: name the file and line where it sits.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A deployment that already failed.** That is `diagnosing-azure-deployments`.

**A design with no change yet.** That is `designing-on-azure`.

**The template as code.** Terraform's structure, modules and state are the Terraform plugin's (issue #295); Bicep style is not reviewed here.

**The vendor-agnostic security disciplines.** A secret in a file, untrusted input reaching a query, a whole object logged when it is not an Azure one: those are the security plugin's skills, which run beside this one.
