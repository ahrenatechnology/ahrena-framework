---
id: testing
type: doc
clade: engineering
subclade: terraform
title: Testing Terraform with terraform test
summary: How a Terraform module is tested beside itself with terraform test, which checks run at plan and which need an apply, how mocks keep a unit test off real infrastructure, what a module's test owes, and where validation blocks and check blocks fit.
references:
  - rules/test-placement.md
  - rules/module-boundaries.md
  - docs/modules.md
---

# Testing Terraform with terraform test

The companion to [`rules/test-placement.md`](../rules/test-placement.md). Terraform's unit is the module, and its test framework is `terraform test` (Terraform 1.6 and later), so that is the tool and the module is what is tested.

## Where the test lives

Beside the module: `modules/<name>/tests/<name>.tftest.hcl`, or `modules/<name>/<name>.tftest.hcl`. `terraform test` runs from the module's directory, looks in `tests/` by default, always loads test files in the directory itself, and HashiCorp recommends not changing the default directory ([`terraform test`](https://developer.hashicorp.com/terraform/cli/commands/test)). A reader opening the module finds the test without a search, and the hook finds a module with none.

## A unit test plans; an integration test applies

A `run` block applies by default, and HashiCorp says plainly that tests "create real infrastructure" unless told otherwise ([Tests](https://developer.hashicorp.com/terraform/language/tests)). For a module's unit test that is the wrong default: it is slow, it costs money, and it needs credentials a pull request's pipeline should not hold.

- **`command = plan`** runs the block without creating anything. Assertions on variables, locals, outputs and planned attributes all work at plan, which covers most of what a module decides: names, tags, counts, which resources exist for which inputs, and every `validation`.
- **`mock_provider`** (Terraform 1.7 and later) replaces a provider with one that returns generated values, so even an apply touches nothing, and **`override_resource`**, **`override_data`** and **`override_module`** pin the values a specific address returns ([Mocks](https://developer.hashicorp.com/terraform/language/tests/mocking)). A data source the module reads, which would otherwise need a real account, is overridden with the value the test needs.
- **A computed attribute is unknown at plan.** An output built from a generated `id` cannot be asserted with a plain plan; by default a mock or override supplies its values only at apply. Set `override_during = plan` on the override (or on the `mock_provider`) and the values are there at plan ([Mocks](https://developer.hashicorp.com/terraform/language/tests/mocking)). A module's `required_version` covers every feature its own test uses.
- **`expect_failures`** names the checkable objects (a variable's validation, a precondition) that a run expects to fail, which is how a test proves the module refuses a bad input.

An apply against real infrastructure is the integration test, and it runs where the credentials are meant to be: a sandbox account, on a schedule or before a release, not on every pull request.

## What a module's test owes

Read in review against the module, each point a `run` block or an assertion:

1. **Every output a caller reads**, with the inputs that produce it.
2. **Every `validation` on a variable**, once with a value it accepts and once with one it refuses (`expect_failures`).
3. **Every branch the inputs select**: each `count` or `for_each` that depends on a variable, at the values that change how many resources exist.
4. **No test prints a sensitive value.** An assertion's `error_message` goes to the log like any other message, so it names what was wrong and never interpolates a secret. Whether a sensitive output is still marked is not a test's job: `rules/outputs.md` condition 1 decides it at commit for every output whose name or value says so.

The test drives the module through its variables only, as a caller would. A test that needs to reach inside, into a resource the module does not output, is a sign the output is missing or the module does too much (`docs/modules.md`).

## Validation, preconditions, postconditions and checks

These are the module's own assertions, and they run in every plan, not only in tests ([Validate your infrastructure](https://developer.hashicorp.com/terraform/language/validate)):

| Mechanism | Since | On failure | Use for |
|---|---|---|---|
| `validation` in a variable | 0.13 | error, operation stops | an input the module cannot accept |
| `precondition` | 1.2 | error, operation stops | an assumption about what the module is given or reads |
| `postcondition` | 1.2 | error, operation stops | a guarantee about what the module produced |
| `check` block | 1.5 | warning, operation continues | a property of the running infrastructure that may change outside Terraform |

A `validation` is the first line of a module's contract and the cheapest test it has: it fails at plan, for every caller, with a message. The message names the rule broken and never repeats a sensitive value, because it goes to the log.

## Running it

`terraform test` from the module's directory, after `terraform init`. That init writes a `.terraform.lock.hcl` in the module's directory. HashiCorp says the lock file "belongs to the configuration as a whole" and lives with the root module ([Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)); in a module's directory it belongs to the test run, so `.gitignore` excludes it (`modules/**/.terraform.lock.hcl`) and the module's tests run against the newest provider its minimum allows, which is what its callers meet. In a pipeline, every module whose files changed runs its test; a root configuration's check is its plan, posted for review (`docs/toolchain.md`). OpenTofu runs the same files with `tofu test` and, from 1.8, prefers a `.tofutest.hcl` over a `.tftest.hcl` of the same name ([What's new in OpenTofu 1.8](https://opentofu.org/docs/v1.8/intro/whats-new/)).

## Where this stops

**Policy is not a test.** "Every bucket is encrypted" across a whole configuration is a policy check over the plan (`docs/toolchain.md`), not a module's test, because it holds for resources the module does not own.

**Third-party test harnesses are not argued.** Terratest and similar tools write integration tests in a general-purpose language; they are a choice a project makes for integration tests that need to call the deployed system. `terraform test` covers the unit level with nothing installed beyond Terraform, which is why it is the default here.
