---
id: drift
type: rule
clade: engineering
subclade: terraform
title: No managed resource is changed outside its code
statement: A Terraform-managed resource changes only by an apply of reviewed code; drift is detected on a schedule and reconciled in code before the next apply.
enforcement: judgment
references:
  - docs/state.md
  - docs/toolchain.md
---

# No managed resource is changed outside its code

Once a resource is in a configuration, the configuration is its definition. A change made in a console, with a CLI, or by another tool is drift: the real object no longer matches either the code or the state, and the next apply of that configuration will try to undo it. HashiCorp's drift tutorial says exactly that of an out-of-band change, Terraform "would attempt to revert your manual changes" ([Manage resource drift](https://developer.hashicorp.com/terraform/tutorials/state/resource-drift)). The emergency fix made at two in the morning is reverted by the routine deploy at ten.

So the rule is not "never touch the console". It is that a change outside code is a debt with a known due date, the next apply, and is paid in code before then.

## Conditions

1. **A managed resource is changed only by an apply of code that went through review.** Decided by review of the pipeline and of the access it grants. The apply runs from a pipeline, from the plan that was reviewed: a plan saved with `-out` and applied by name applies exactly what was planned ([`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan)), and the saved plan is a sensitive artifact that stays out of the repository and out of the log (`rules/state.md`, `rules/outputs.md`). People hold read access to production by default; write access outside the pipeline is the break-glass case of condition 3.

2. **Drift is looked for on a schedule, not discovered at the next change.** Decided by the presence of a scheduled job, read in review. The job runs `terraform plan -detailed-exitcode` against each environment's root configuration; exit code 2 means the plan is not empty ([`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan)), and on a configuration whose code has not changed since its last apply, a non-empty plan is drift. `terraform plan -refresh-only` then shows what moved, without proposing to change it. HCP Terraform runs the same detection as a product feature; a pipeline job is the vendor-neutral form. The schedule is the project's to set, against how often its environments are touched.

3. **A change made outside code is reconciled in code before the next apply of that configuration.** Decided by review. The deadline is not a number of hours; it is the event that would revert the change. Reconciling means one of two things, and the tutorial walks both: the change is wanted, so the configuration is edited to say it and a refresh-only apply records the real object in state; or it is not wanted, and an ordinary apply reverts it on purpose.

4. **An existing object is brought under management by an `import` block, renamed by a `moved` block, and released by a `removed` block.** Decided by review. Configuration-driven import (Terraform 1.5 and later) puts the import in the reviewed change rather than in someone's shell history ([Import](https://developer.hashicorp.com/terraform/language/import)); `moved` (Terraform 1.1 and later) renames an address without destroying the object ([Refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring)); `removed` with `lifecycle { destroy = false }` takes an object out of state without destroying it ([`removed` block](https://developer.hashicorp.com/terraform/language/block/removed)). `terraform import`, `terraform state mv` and `terraform state rm` do the same from a terminal, unreviewed, and are reserved for recovery.

5. **Each resource is managed by one configuration, with one tool.** Decided by review. Two configurations, or Terraform and another provisioning tool, managing the same object will each see the other's changes as drift and revert them in turn.

6. **`ignore_changes` names the attributes another system owns, and says which system.** Decided by review. Some drift is expected: an autoscaling group's desired count, a tag a cost tool adds. Excluding it in code, with `lifecycle { ignore_changes = [...] }`, is how condition 2 stays quiet about it, and the exclusion is reviewed like any other line. The list names attributes, never `all`, and a comment beside it points at the issue that records which system owns them; `ignore_changes = all` turns this rule off for that resource.

## Where this stops

**None of this is decidable from the repository.** Drift is a property of the real infrastructure, and only a plan against it reports drift. The rule names that plan as the detector and leaves running it to the project's pipeline, which is why it declares judgment: there is no hook to stand in for it.

**Restricting human write access is a cloud's mechanism.** How production write access is limited (an organisation policy, a role boundary, a separate account) is specific to each cloud and belongs to that cloud's plugin. This rule requires that the pipeline is the normal writer; it does not say how a cloud enforces it.

**OpenTofu behaves the same.** `tofu plan -detailed-exitcode`, `import`, `moved` and `removed` carry the same meaning; `removed` arrived in OpenTofu 1.7 ([What's new in OpenTofu 1.7](https://opentofu.org/docs/v1.7/intro/whats-new/)).
