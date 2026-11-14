---
id: libraries
type: doc
clade: engineering
subclade: terraform
title: Recommended tools and providers for Terraform, per problem
summary: For each problem a Terraform repository meets - testing, linting, security scanning, policy, documentation, pull-request automation, utility resources, secrets - the tool or provider this framework recommends, why, and when not to use it.
references:
  - docs/toolchain.md
  - docs/testing.md
  - docs/modules.md
  - rules/pinning.md
---

# Recommended tools and providers for Terraform, per problem

Each row names one choice, the premise that decides it, and the case where something else is the better choice. A recommendation here is a starting point a project departs from with a reason, never a requirement; the rules require outcomes, not tools. Cloud-specific providers and registry modules are not here: they belong to the cloud's plugin.

The premises are the framework's: maintainability, low complexity, no circular reference, and, for a tool that runs on a pull request, that it needs no credentials.

| Problem | Recommended | Why | When not |
|---|---|---|---|
| Testing a module | `terraform test`, with `command = plan` and `mock_provider` ([Tests](https://developer.hashicorp.com/terraform/language/tests)) | ships with Terraform 1.6+, tests sit beside the module, runs with no credentials when it plans or mocks (`docs/testing.md`) | an integration test that must call the deployed system over the network: Terratest, written in Go, in a sandbox account |
| Formatting | `terraform fmt -check -recursive` ([fmt](https://developer.hashicorp.com/terraform/cli/commands/fmt)) | the canonical style is the tool's, so nothing is left to argue | never |
| Linting | tflint with the bundled Terraform ruleset (`recommended`, on by default) plus the provider's ruleset ([tflint](https://github.com/terraform-linters/tflint)) | Terraform has no linter of its own; the style guide points to tflint ([Style guide](https://developer.hashicorp.com/terraform/language/style)) | a repository already gated by an equivalent scanner rule for every condition it would add |
| Static security scanning | Trivy (`trivy config`) | scans `.tf` files and plan JSON ([Trivy, Terraform](https://trivy.dev/latest/docs/coverage/iac/terraform/)); tfsec's maintainers moved its development into Trivy, so a new project starts there ([tfsec](https://github.com/aquasecurity/tfsec)) | a team already on Checkov, which scans `.tf` files and plan JSON equally ([Checkov, plan scanning](https://www.checkov.io/7.Scan%20Examples/Terraform%20Plan%20Scanning.html)); one scanner, not two |
| Organisation policy over the plan | Conftest with Rego over the plan JSON ([Conftest](https://www.conftest.dev/)) | vendor-neutral, policies are code in the repository, runs in any pipeline | on HCP Terraform, its own policy enforcement (Sentinel, OPA, or the HCL-based Terraform policy on 1.17+) runs in the same place as the plan ([Policy enforcement](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement)) |
| Validating inputs and outputs | `validation`, `precondition`, `postcondition`; `check` for properties that drift ([Validate](https://developer.hashicorp.com/terraform/language/validate)) | in the language, evaluated in every plan for every caller | a rule about many modules at once, which is policy (row above) |
| Module documentation | terraform-docs, generating the README's inputs and outputs ([terraform-docs](https://terraform-docs.io/)) | the README the standard module structure asks for, kept true by a tool | a module with two variables, whose README is shorter by hand |
| Pull-request automation | the project's own pipeline running `docs/toolchain.md`'s steps | no second system holding credentials; the steps are visible in the repository | on HCP Terraform, its runs and workspaces; a team with many roots and no pipeline platform, Atlantis |
| A resource with only a lifecycle (a trigger, a stored value) | `terraform_data` ([terraform_data](https://developer.hashicorp.com/terraform/language/resources/terraform-data)) | built in, "without requiring or configuring a provider" | an existing configuration on `null_resource` that works, where the migration is churn |
| Random names and generated values | `hashicorp/random` | a value generated once and kept in state, stable across plans | a generated secret, which belongs in a secret manager with the value never in state (`docs/state.md`) |
| A secret a resource needs | an ephemeral resource from the cloud's provider, passed through a write-only argument where the resource has one ([Ephemeral values](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/ephemeral)) | Terraform 1.10/1.11+; the value reaches neither state nor plan | an older Terraform or a provider without them: a `sensitive` variable from the pipeline's secret store, and state treated accordingly |
| Choosing the CLI | Terraform, or OpenTofu, one per configuration | the language is shared and the rules hold for both | a repository that needs client-side state encryption, which only OpenTofu has (`docs/state.md`) |

## Where this stops

**No cloud provider and no registry module is recommended here.** Which network module, which cluster module, which provider version for AWS, Google Cloud or Azure belongs to the cloud's plugin, which can read that cloud's practices.

**No version is pinned here.** A version in a document is wrong at the next release; `rules/pinning.md` requires the project to pin, and the lock file holds the choice.

**Wrappers are not recommended or refused.** Terragrunt and similar tools solve repeated backend and provider configuration across many roots; a project weighs that against a second tool in its chain. Nothing in this plugin depends on one.
