---
id: secrets
type: rule
clade: engineering
subclade: terraform
title: No secret in a variable default, an argument literal or a versioned tfvars file
statement: A Terraform secret has no default, is marked sensitive or ephemeral, and is never written as a literal in a .tf or a versioned .tfvars file.
enforcement: hook
enforced-by: hooks/check-terraform.py
references:
  - docs/state.md
  - docs/toolchain.md
---

# No secret in a variable default, an argument literal or a versioned tfvars file

A secret written into Terraform source is in three places at once: the repository, every state snapshot, and every saved plan. HashiCorp's [Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data) says the second and third outright, and the first is what a literal is. Marking the variable `sensitive` removes it from the CLI's output and from nowhere else.

The way in is the variable, with no default, filled at run time. The value comes from the environment (`TF_VAR_<name>`, which the [variables page](https://developer.hashicorp.com/terraform/language/values/variables) describes for exactly this, injecting values in a pipeline without writing a file), from an ephemeral resource that reads it from a secret store, or from an unversioned `.tfvars` file. HashiCorp's style guide lists "any `.tfvars` files that contain sensitive information" among the files never to commit ([Style guide](https://developer.hashicorp.com/terraform/language/style)).

Where the version allows it, the value never reaches state at all. An `ephemeral = true` variable (Terraform 1.10 and later) is omitted from state and plan files, and a write-only argument such as `password_wo` (Terraform 1.11 and later) is sent to the provider and not stored ([Ephemeral values in resources](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/ephemeral)). `docs/state.md` argues when to use which.

## Conditions

Each of these is decided by `hooks/check-terraform.py`. A secret's name is one whose words include `password`, `passwd`, `passphrase`, `secret`, `token`, `credential`, `private_key`, `api_key`, `access_key` or `connection_string`, and that does not end in a word naming the secret rather than holding it (`_id`, `_arn`, `_name`, `_version`, `_length`, `_ttl`, `_type`, `_path`, `_url`, `_endpoint` and the like). `db_password` is a secret; `db_password_secret_arn` and `password_wo_version` are not.

1. **A secret-named variable has no default, or `default = null`.** A default is a literal in the source, read by every plan that does not override it. `null` is accepted because it is how an optional secret says "absent" without carrying one.

2. **A secret-named variable is marked `sensitive = true` or `ephemeral = true`.** Without either, the value is printed in plan and apply output and in any expression derived from it. `sensitive` is available from Terraform 0.15 and `ephemeral` from 1.10 ([Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)); [Variable block](https://developer.hashicorp.com/terraform/language/block/variable) defines both.

3. **No secret-named argument, in any block, is given a string literal.** A provider's `access_key`, a backend's `password`, a resource's `password_wo`, a local named `api_token`: each is a secret in the repository. A write-only argument keeps the value out of state and plan, not out of the source, so a literal there is a finding like any other. A reference (`var.db_password`, `ephemeral.<type>.<name>.value`) is the correct form and passes. HashiCorp says the same of backends: credentials belong in environment variables, not in the block ([Backend block](https://developer.hashicorp.com/terraform/language/backend)).

4. **No `.tfvars` file in the repository gives a secret-named variable a literal.** Read over the files git tracks or would add, so a `secrets.auto.tfvars` that `.gitignore` excludes is not reported. `*.auto.tfvars` and `terraform.tfvars` are loaded without being named, which makes a committed one the quietest way to ship a secret into every plan.

## Where this stops

**The name is the detector, and a secret under another name passes.** `variable "db" { default = "hunter2" }` is a secret this hook cannot see. The baseline review discipline that sweeps every added line for a credential, `ahrena-engineering-security:skills/reviewing-secrets/SKILL.md`, reads the value rather than the name and is routed on every change; this rule is the Terraform-shaped half that holds at write time.

**A literal is a quoted string with no interpolation.** `"${var.prefix}-token"` is an expression and passes, because its value is not written down. A heredoc is not read.

**`.tfvars.json` and `.tf.json` files are not parsed.** JSON configuration is rare in hand-written Terraform; a repository that generates it reviews the generator.

**Condition 2 does not decide `ephemeral` against the root module.** An ephemeral root variable cannot reach state, which is the stronger guarantee, but it can only be referenced from ephemeral contexts. Which of the two a variable needs depends on where it flows, and `docs/state.md` says how to choose.
