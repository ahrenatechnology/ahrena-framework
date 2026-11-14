---
name: reviewing-terraform
description: Use when a change under review edits Terraform or OpenTofu (.tf, .tofu, .tfvars, .tftest.hcl, .terraform.lock.hcl) and the question is what an infrastructure reader would catch - state that can leak or race, a secret in source, an output that exports a policy, a credential, a connection string or a whole object, an unpinned provider or module, a module that configures its own provider, a change made outside code. Reads the routed files against this plugin's rules and the TF conditions; every finding names the condition.
type: skill
clade: engineering
subclade: quality
references:
  - rules/state.md
  - rules/secrets.md
  - rules/outputs.md
  - rules/pinning.md
  - rules/drift.md
  - rules/module-boundaries.md
  - rules/test-placement.md
  - docs/modules.md
  - docs/toolchain.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Terraform

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` and the baseline secrets sweep have already read the change. This skill reads what needs a Terraform reader. The conditions are in `references/conditions.md`, identified as `TF-n`; a finding cites the identifier, and severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `terraform` route on the changed `.tf`, `.tofu`, `.tfvars`, `.tftest.hcl`, `.tofutest.hcl` and `.terraform.lock.hcl` files and on any committed state or plan file, and the `terraform-pipeline` route on a script or pipeline file whose added lines run `terraform` or `tofu`. Those are the files this skill reads. When no router ran (a person or an agent called this skill directly), select the same files by hand: the changed files those two routes in `ahrena-engineering-quality:skills/reviewing-diffs/references/routes.json` would match.

Before the conditions, read how the repository runs Terraform: which CLI and version (`required_version`, the lock file), which backend each root uses, its `modules/` layout, its `.tflint.hcl`, its scanner configuration and its pipeline. What a green check already decided (tflint, the scanner, `terraform validate`) is not reported again.

## 2. Run the hook

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/check-terraform.py" <checkout>
```

Every failure it prints names a rule and a condition, and is a finding as it stands, at the severity the tests of `ahrena-engineering-quality:docs/review-findings.md` give it (blocking on a line the change introduces or edits). A failure on a line the change did not touch, and that the change did not cause, is recorded as deferrable, as that document says, so the next person has it; it does not gate this change. To tell the two apart, run the hook on the base revision too (`git archive <base>` into a scratch folder) and compare.

## 3. Read the conditions the hook cannot decide

Open `references/conditions.md` and work through the conditions marked `review`, in the order the file gives them. They are the ones that need a reader: whether the backend actually locks and encrypts, whether an output that locates something has a consumer, whether a module receives its dependencies or creates them, whether the plan shows a replacement the author did not mean.

## 4. Read beyond the hunk

For each output the change adds, find who reads it: another root's data source, a pipeline step, a `terraform_remote_state`. For each variable it adds, find what the callers pass. For each resource it changes, read the plan if the pipeline posted one, and look for `must be replaced` and `destroy`: a renamed address without a `moved` block destroys and recreates the object.

Read what the change replaced, from the base revision, before calling a changed line wrong.

## 5. Write the findings

Each finding carries the four fields of `ahrena-engineering-quality:docs/review-findings.md`, with the `TF-n` identifier, and a correction that is an instruction: the file and line, what to write instead. A finding that would quote a secret names the file, the line and the variable the value should come from, never the value.

Hand the set back to `reviewing-diffs`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A cloud's design.** Whether the bucket should be public, the role's permissions, the network's shape: those are the cloud plugin's review and the security disciplines (`reviewing-access`, `reviewing-sensitive-data`). This skill reads the Terraform that expresses the design, not the design.

**A pipeline file that runs Terraform.** The supply-chain discipline reads the pipeline definition; this skill reads a pipeline line only for what `TF-3` and `TF-9` name.

**Another language in the same change.** A `.py` or `.ts` file is read by that language's skill.
