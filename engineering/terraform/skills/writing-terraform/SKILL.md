---
name: writing-terraform
description: Use when writing or changing Terraform (.tf, .tfvars, .tftest.hcl) - a new module, a new root configuration for an environment, a resource added to one - so that it is written test-first against this plugin's rules from the first line - state on a locked remote backend, no secret in source, outputs as an allowlist, providers and modules pinned, calls running one way, a test beside each module. Writes the code; it does not review a diff or diagnose a failed plan.
type: skill
clade: engineering
subclade: terraform
references:
  - rules/state.md
  - rules/secrets.md
  - rules/outputs.md
  - rules/pinning.md
  - rules/drift.md
  - rules/module-boundaries.md
  - rules/test-placement.md
  - docs/modules.md
  - docs/state.md
  - docs/testing.md
  - docs/toolchain.md
  - docs/libraries.md
---

# Writing Terraform

Terraform is written variables first and test first: the module's interface, then a failing `terraform test` against it, then the resources that make the test pass, then the outputs a caller reads, then the toolchain. Every rule of this plugin applies from the first line, not at review.

## 1. Read the repository before writing anything

Read how this repository already writes Terraform: its root configurations and their backends, its `modules/`, its `versions.tf` or `terraform.tf`, its `.tflint.hcl`, its pipeline, its `AGENTS.md` and `CLAUDE.md`. If the project keeps a component map, resolve the names you are about to create against it with `ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md`. Note which CLI it applies with, Terraform or OpenTofu, and which version; the lock file and `required_version` say.

Output: the CLI and version, the backend in use, the module layout, and where the new code goes.

## 2. Decide what kind of module this is

Read `docs/modules.md` and place the change.

- **A new environment** is a root configuration: its own directory, its own backend, calling existing modules. It owns state and configures providers.
- **A group of resources two roots need** is a reusable module under `modules/<name>/`: variables, resources, outputs, a `tests/` folder. No provider block, no backend (`rules/module-boundaries.md`).
- **One resource with a few arguments** is written inline in the root; a module that wraps one resource adds a layer and decides nothing.
- **An existing module needs a new behaviour** is a new module that calls it, or a new variable on it with a default that keeps today's behaviour. Never an edit for one caller's case.

Output: the module's kind, its directory, and what calls it.

## 3. Write the interface: variables, then outputs' names

In `variables.tf`, one `variable` block per input the module needs, each with a `type`, a `description`, and a `validation` wherever a value can be wrong in a way the module can name. Take dependencies as inputs, the ids and names of what the caller already has, never by creating or looking them up inside (`docs/modules.md`, inversion of control). Take the two attributes the module reads, not a whole object.

A secret is a variable with no default and `sensitive = true`, or `ephemeral = true` where it only flows into ephemeral contexts and the Terraform version is 1.10 or later. It arrives at run time from `TF_VAR_<name>` or an ephemeral resource, never as a literal (`rules/secrets.md`, `docs/state.md`).

Write the names of the outputs a caller will read, and nothing else. Each is a named attribute; an output that could carry a secret, a policy or a connection string is `sensitive = true`; a root exports no whole object; an output describing access or topology exists only for a consumer you can name (`rules/outputs.md`).

Output: the module's interface, and for each output the consumer that reads it.

## 4. Write the test, and watch it fail

In `modules/<name>/tests/<name>.tftest.hcl`, one `run` block per behaviour the interface promises, with `command = plan` and `mock_provider` or `override_data` wherever a real account would otherwise be needed (`docs/testing.md`). Cover every output a caller reads, every `validation` with a value it accepts and one it refuses (`expect_failures`), and every `count` or `for_each` the inputs drive. No assertion's `error_message` interpolates a sensitive value.

Run it with `terraform test` from the module's directory and confirm it fails for the reason you expect: the resources do not exist yet. A test that passes before the code exists tests nothing. The red-then-green discipline is `ahrena-engineering-backend:skills/driving-with-tdd/SKILL.md`; follow it, with `terraform test` as the runner.

Output: the test file and its red run.

## 5. Write the resources until the test passes

- **Versions first.** `terraform.tf` holds `required_version` and a `required_providers` entry, with `source` and `version`, for every provider the module uses. A root bounds each from above with `~>`; a reusable module states only a minimum with `>=`. A registry module call takes an exact `version`; a git one a `?ref=` tag or commit (`rules/pinning.md`).
- **Backend, in a root only.** A remote backend that locks and encrypts at rest, declared partially, with credentials from the environment and never in the block or on a `-backend-config` command line (`rules/state.md`). The settings for a given cloud's backend are in that cloud's plugin.
- **Resources.** One concern per file; the style guide's names (`main.tf`, `variables.tf`, `outputs.tf`, `locals.tf`, `providers.tf`, `backend.tf`) first, then a file per concern. `count` for near-identical resources, `for_each` otherwise, and sparingly. A secret reaches a resource by a reference, through a write-only argument where the provider has one. An expression that grows past one reading moves to a named local.
- **Bringing in what already exists** is an `import` block in the change, a rename is a `moved` block, a release is a `removed` block with `destroy = false` (`rules/drift.md`).

Hold every file and every block to the single-responsibility limits of [`clean-code.md`](../../../fundamentals/rules/clean-code.md), [`kiss.md`](../../../fundamentals/rules/kiss.md) and [`solid.md`](../../../fundamentals/rules/solid.md). No Terraform tool measures them in HCL: the structure hook parses Python only, and tflint reports unused declarations and untyped variables, not size. So the limit is held by writing to it, and a reviewer reads it.

Run `terraform test` until it passes. Output: the code and the green run.

## 6. Run the toolchain, in order

From the repository root, the steps of `docs/toolchain.md` that need no credentials:

```sh
terraform fmt -check -recursive
terraform init -backend=false && terraform validate
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/check-terraform.py" .
tflint --recursive
```

Then the project's security scanner, if it has one (`docs/libraries.md`). Fix every finding; a hook finding names the rule and condition it breaks and says what to write instead. A root configuration's plan runs in the pipeline, with read-only credentials, and is what the reviewer reads; never print `terraform output -json` or `terraform show -json` to a log while checking your work.

Output: each command with its result.

## 7. Hand back

Return the files written, the red and the green test runs, the toolchain results, and, for every output the change adds, the consumer that reads it. Do not apply. An apply runs from the pipeline, from the reviewed plan, after merge.

## When this skill does not apply

**Reviewing someone else's Terraform.** That is `skills/reviewing-terraform/SKILL.md`, which reads a diff against the same rules and reports findings.

**A failed plan, a failed apply, a stuck lock or drift.** That is `skills/debugging-terraform/SKILL.md`.

**Which cloud resources, IAM or network design to use.** The cloud's plugin owns its services, its identity model and its backend's settings. This skill writes whatever that design is, in Terraform's shape.

**Applying to an environment.** No step here runs `terraform apply`. Infrastructure changes reach an environment through the pipeline.
