---
id: toolchain
type: doc
clade: engineering
subclade: terraform
title: The Terraform toolchain, and what a pipeline may show
summary: Which tools run on a Terraform change and in what order - fmt, validate, tflint, a static security scanner, terraform test, plan - what each decides and what it cannot, what the plan log of a pipeline may and may not show, and how the apply is gated.
references:
  - rules/state.md
  - rules/outputs.md
  - rules/pinning.md
  - rules/drift.md
  - docs/testing.md
  - docs/libraries.md
---

# The Terraform toolchain, and what a pipeline may show

The companion to [`rules/pinning.md`](../rules/pinning.md) and to the pipeline half of [`rules/state.md`](../rules/state.md) and [`rules/outputs.md`](../rules/outputs.md). It argues an order and a boundary; the pipeline file is the project's to write.

## The order, cheapest first

Every step below runs on a pull request, in this order, and each one that fails stops the rest. The order is by cost and by what each step needs: the first four need no credentials at all.

1. **`terraform fmt -check -recursive`.** Formats to the canonical style and, with `-check`, exits non-zero listing the files that are not ([`terraform fmt`](https://developer.hashicorp.com/terraform/cli/commands/fmt)). The style guide asks for `fmt` and `validate` before every commit and recommends a pre-commit hook for `fmt` ([Style guide](https://developer.hashicorp.com/terraform/language/style)). Formatting is settled by the tool, never discussed in review.
2. **`terraform validate`**, after `terraform init -backend=false`. Checks that the configuration is syntactically valid and internally consistent, "regardless of any provided variables or existing state", and "does not validate remote services, such as remote state or provider APIs" ([`terraform validate`](https://developer.hashicorp.com/terraform/cli/commands/validate)). It needs providers installed and no credentials.
3. **The plugin's hook and tflint.** `hooks/check-terraform.py` decides the conditions of this plugin's rules with nothing installed. tflint adds what HashiCorp's style leaves to a linter, which Terraform does not have: its bundled Terraform ruleset enables a `recommended` preset by default, and its README recommends installing the provider ruleset for AWS, Azure or Google where the configuration uses that provider ([tflint](https://github.com/terraform-linters/tflint)). Of the recommended rules, `terraform_required_version`, `terraform_required_providers`, `terraform_module_pinned_source` and `terraform_module_version` overlap `rules/pinning.md`; `terraform_unused_declarations` and `terraform_typed_variables` are worth the most beyond it ([rules](https://github.com/terraform-linters/tflint-ruleset-terraform/blob/main/docs/rules/README.md)). `terraform_documented_variables` and `terraform_documented_outputs` are not in the preset and are worth turning on for reusable modules.
4. **A static security scanner over the configuration.** Trivy or Checkov (`docs/libraries.md`) read the `.tf` files against a library of misconfiguration policies: an unencrypted store, a public endpoint, a wildcard permission. They are the policy layer this plugin does not write, because their policies are per cloud.
5. **`terraform test`** for every module whose files changed (`docs/testing.md`). Unit tests plan or mock, so they need no cloud credentials either.
6. **`terraform plan -out=<file>`** for every root configuration the change touches, with read-only credentials, against the real state. This is the step a reviewer reads, and the one whose output needs the boundary below.

The plan's JSON (`terraform show -json <file>`, written to a file) can then be scanned by the same scanner or by a policy tool, which sees resolved values the static scan could not. Apply comes after merge, not here.

## What a plan log may show

A pipeline log is an exit, in the sense of the exposure rule of issue #294: more people read it than read state, it is kept longer than anyone remembers, and on a public repository's fork it may be visible to the world. Terraform redacts sensitive values in the plan and apply output of the CLI ([Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)), and that redaction is the only thing standing between a secret and the log. So:

- **The human-readable plan may be printed**, and posted on the pull request, because that is what review reads. It is only as safe as the marking: a secret in an unmarked variable or output prints in clear (`rules/secrets.md`, `rules/outputs.md`).
- **The JSON plan and the outputs are never printed.** `terraform show -json` prints sensitive values from state in plain text ([`terraform show`](https://developer.hashicorp.com/terraform/cli/commands/show)), the JSON format marks sensitive values beside them rather than masking them ([JSON output format](https://developer.hashicorp.com/terraform/internals/json-format)), and `terraform output -json` or `-raw` prints sensitive outputs in plain text ([Output block](https://developer.hashicorp.com/terraform/language/block/output)). Each is written to a file the job keeps private and deletes, or read one named field at a time. `rules/outputs.md` condition 3 decides the printing.
- **The saved plan file is an artifact with the state's sensitivity.** It holds the full configuration and the planned values in cleartext ([`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan)). It is passed from the plan job to the apply job through the pipeline's private storage, never attached to a pull request, never uploaded as a public artifact, and deleted after the apply.
- **Debug logging stays off in a pipeline.** `TF_LOG` writes detailed logs to standard error ([Environment variables](https://developer.hashicorp.com/terraform/cli/config/environment-variables)); HashiCorp's page does not say they are redacted, so a pipeline treats them as unredacted and enables them only in a private rerun.
- **The backend's settings stay out of the log.** Credentials go in environment variables, never `-backend-config` on a command line that the pipeline echoes ([Backend block](https://developer.hashicorp.com/terraform/language/backend)).

## Applying

The apply runs from the pipeline, after merge, from the plan file the reviewed run saved, so what was approved is what is applied (`rules/drift.md`). An environment that needs a person's approval before apply gets it in the pipeline's own approval step, against that plan. Production applies run with the only identity that can write production state; locking stays on (`rules/state.md`).

## Terraform or OpenTofu

One CLI per configuration, the one the pipeline applies with; the lock file is that CLI's (`rules/pinning.md`). The language is shared and the rules here hold for both. OpenTofu reads `.tofu` files and prefers one over a `.tf` of the same name, which lets a repository carry OpenTofu-only syntax without breaking Terraform ([OpenTofu files](https://opentofu.org/docs/language/files/)); a repository that does that has chosen OpenTofu.

## Where this stops

**The pipeline file is not here.** Which CI system, how jobs share the plan file, how approvals are configured: each is the platform's. This page states what each step decides and what may leave it.

**Cost estimation is not covered.** A plan priced before apply is useful and is a product choice, not a rule.

**Pull-request automation is a choice.** Atlantis, HCP Terraform and a plain pipeline all run the same steps; `docs/libraries.md` argues the choice.
