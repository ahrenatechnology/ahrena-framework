---
id: pinning
type: rule
clade: engineering
subclade: terraform
title: Terraform, providers and modules are pinned, and the lock file is committed
statement: Terraform declares required_version and every provider's version; modules are pinned to an exact version or a tag; the root commits .terraform.lock.hcl.
enforcement: hook
enforced-by: hooks/check-terraform.py
references:
  - docs/toolchain.md
  - docs/libraries.md
---

# Terraform, providers and modules are pinned, and the lock file is committed

A plan is only reviewable if the code that produced it is the code that will apply it. Terraform pulls three kinds of code at `init`: the CLI itself, providers, and remote modules. Each is a third party's code that runs with the configuration's credentials, and each moves on its own schedule. HashiCorp's style guide pins them for the stated reason, "to prevent provider and module upgrades from introducing unintentional changes" ([Style guide](https://developer.hashicorp.com/terraform/language/style)).

The two kinds of dependency are pinned differently, and the difference is HashiCorp's. Providers are recorded in `.terraform.lock.hcl`, which tracks "only provider dependencies" and belongs in version control; remote modules are not recorded anywhere, and Terraform takes the newest version the constraint allows unless the constraint is exact ([Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)). So a provider can take a range and let the lock file hold the selection, and a module cannot.

This rule is also the supply-chain discipline for infrastructure code: the conditions `ahrena-engineering-security:skills/reviewing-supply-chain/SKILL.md` reads in a package manifest, in the shape Terraform gives them.

## Conditions

Each of these is decided by `hooks/check-terraform.py`, over every root and reusable module. Conditions 1, 2 and 4 are also what [tflint's Terraform ruleset](https://github.com/terraform-linters/tflint-ruleset-terraform/blob/main/docs/rules/README.md) checks with `terraform_required_version`, `terraform_required_providers`, `terraform_module_version` and `terraform_module_pinned_source`, all four in its `recommended` preset; a project that runs tflint gets those twice, and a project that runs nothing still gets all five once. Conditions 3 and 5 have no tflint rule.

1. **A `terraform` block declares `required_version`.** It states which CLI versions may run the configuration ([`terraform` block](https://developer.hashicorp.com/terraform/language/block/terraform)). Without it, an older CLI fails on syntax it does not know, and a newer one applies a configuration nobody tested on it.

2. **Every provider the module uses is declared in `required_providers` with a version constraint.** HashiCorp: "Each Terraform module must declare which providers it requires", and the version is optional only in the sense that leaving it out accepts any version ([Provider requirements](https://developer.hashicorp.com/terraform/language/providers/requirements)). A provider counts as used when a resource, data source or ephemeral resource carries its prefix, or a `provider` block names it. Child modules inherit provider configurations and not requirements, so each declares its own.

3. **A root module bounds each provider from above; a reusable module states only a minimum.** Both halves are HashiCorp's. Root modules "should use a `~>` constraint to set both a lower and upper bound" ([Version constraints](https://developer.hashicorp.com/terraform/language/expressions/version-constraints)), so a major upgrade is a change somebody makes on purpose. A shared module should "constrain only the minimum required provider version using a `>=` constraint" and not use `~>` or any maximum ([Providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers), [Provider requirements](https://developer.hashicorp.com/terraform/language/providers/requirements)), because a module that caps a provider forces its ceiling on every configuration that calls it, and two modules with different ceilings cannot be called together.

4. **A registry module takes an exact `version`; a git module takes a `?ref=` that is a tag or a commit.** A registry source with no `version`, or with a range, takes whatever is newest at the next `init`; HashiCorp's practice for modules is to "require specific versions" and its lock-file page says an exact constraint is how Terraform "will always select the same module version". A git source with no `ref` follows the default branch ([Module sources](https://developer.hashicorp.com/terraform/language/modules/sources)), and a `ref` that names a branch (`main`, `master`, `develop`, `trunk`, `HEAD`) does the same with more words. A local path (`./`, `../`) is the same commit as the caller and needs nothing.

5. **Every root module that uses a provider has `.terraform.lock.hcl` beside it, in the repository.** HashiCorp: "You should include this file in your version control repository" ([Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)), and the style guide lists it under what to always commit. It records the selected version and its checksums; without it, the next `init` resolves the range again on another machine.

## Where this stops

**Condition 4 reads the source string.** A registry source is recognised by its `namespace/name/provider` shape, optionally behind a host; a git source by `git::`, `git@`, `github.com/` or `bitbucket.org/`. Other sources (`s3::`, `gcs::`, an HTTP archive) are not decided, and a reviewer reads them. Whether a `ref` that is not a branch name is a tag or a branch with another name is not decided either; a project that names branches `release` and passes `?ref=release` passes.

**Condition 3 decides the shape of the constraint, not its value.** `~> 0.1` on a provider at 5.x passes.

**A reusable module in the same repository is still a reusable module.** Condition 3 asks a module under `modules/` for a minimum, though only one root calls it today. HashiCorp's guidance is written for modules "you intend to reuse across many configurations", and a module that is never meant to be reused is a candidate for inlining into its root, which `docs/modules.md` argues.

**`.tf.json` is not read.** Nor is a provider version set through a deprecated `version` argument inside a `provider` block, which Terraform still accepts and this hook does not count as a constraint.

**OpenTofu reads the same constraints and its own lock file, from its own registry.** The rule is unchanged; the selected versions differ, because OpenTofu resolves providers against a separate registry ([OpenTofu FAQ](https://opentofu.org/faq/)). A repository that runs both CLIs commits the lock file of the one its pipeline applies with.
