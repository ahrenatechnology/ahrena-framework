---
name: debugging-terraform
description: Use when Terraform fails or surprises - init, validate or plan errors, an apply that failed halfway, a state lock that will not release, a plan that wants to replace or destroy what nobody changed, or drift between the real infrastructure and the code. Reproduces the failure without writing anything, classifies it, and fixes it in code; state is changed through reviewed blocks, never by hand, and nothing sensitive is printed while diagnosing.
type: skill
clade: engineering
subclade: terraform
references:
  - rules/state.md
  - rules/drift.md
  - rules/outputs.md
  - rules/pinning.md
  - docs/state.md
  - docs/toolchain.md
---

# Debugging Terraform

A Terraform failure is diagnosed from a plan, never from an apply, and fixed in code. The table of symptoms, causes and fixes is `references/failures.md`.

## 1. Stop writing, and keep the evidence private

Do not re-run the failed apply. Do not run `terraform apply`, `terraform state` subcommands, `force-unlock` or `-lock=false` while diagnosing; each one writes, and the second write is what turns a failure into an outage. Keep every output that could hold a value off shared logs: no `terraform output -json`, no `terraform show -json`, no `TF_LOG` in a pipeline (`docs/toolchain.md`). Debug logging, when it is needed, runs locally with `TF_LOG_PATH` pointing at a file you delete afterwards.

Output: the failing command, its exit code and the error text, with any value that could be a secret replaced by the variable it came from.

## 2. Reproduce with a plan

Run, from the failing root configuration and with the same CLI version as the pipeline:

```sh
terraform init
terraform validate
terraform plan -detailed-exitcode -out=diagnose.tfplan
```

Exit 0 means the plan is empty, 1 an error, 2 a non-empty plan. Keep `diagnose.tfplan` out of the repository and delete it when done (`rules/state.md`). If the plan proposes changes nobody made in code, also run `terraform plan -refresh-only` to see what moved in the real infrastructure.

Output: which of the three it is, and the first error or the list of addresses the plan would change.

## 3. Classify the failure

Open `references/failures.md` and find the row whose symptom matches. Each row names the class (configuration, version, state, lock, provider, drift, partial apply), the usual cause, how to confirm it, and the fix. A failure that matches no row is read from the provider's error text: the resource address and the API's message say which argument was refused.

Output: the class, the cause, and the evidence that confirms it.

## 4. Fix it in code

Every fix is a change to configuration that goes through review and a reviewed plan:

- **An object that exists and is not in state** is adopted with an `import` block; one renamed in code keeps its object with a `moved` block; one that should leave Terraform's management goes with a `removed` block and `destroy = false` (`rules/drift.md`).
- **A version problem** is fixed in the constraint and the lock file (`terraform init -upgrade` only when the change means to move versions), never by deleting the lock file (`rules/pinning.md`).
- **Drift** is resolved one of two ways, decided with whoever made the change: wanted, so the code is edited to say it and a refresh-only apply records it; unwanted, so an ordinary apply reverts it on purpose (`docs/state.md`).
- **A stale lock** is released by its owner. Confirm from the lock's ID and who holds it that no run is in progress; only then does the owner run `terraform force-unlock <id>`, which HashiCorp reserves for one's own lock after automatic unlocking failed.

Run the plan again. The fix is done when the plan shows exactly what was meant and nothing else.

Output: the change, and the plan before and after.

## 5. Hand back

Return the class, the cause, the evidence, the change and the clean plan. The apply runs from the pipeline, after review. If the failure exposed a value somewhere it should not be (a secret in a log, state in an artifact), say which and that it must be rotated.

## When this skill does not apply

**Writing new Terraform** is `skills/writing-terraform/SKILL.md`; **reviewing a change** is `skills/reviewing-terraform/SKILL.md`.

**A cloud's own failure.** A quota, a permission the identity lacks, a service limit: the provider's error names it, and the cloud's plugin says what to change on that side. This skill takes the failure as far as the provider's message and the Terraform change it needs.

**Recovering a corrupted or lost state.** Restoring from the backend's version history is an operation on production state, done by the people who own it, with the backend's own tools. This skill stops at saying that is what is needed.
