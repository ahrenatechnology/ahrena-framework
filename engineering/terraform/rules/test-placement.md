---
id: test-placement
type: rule
clade: engineering
subclade: terraform
title: The test sits beside the module it tests
statement: Every reusable Terraform module has a .tftest.hcl file in its own folder or in its tests/ folder.
enforcement: hook
enforced-by: hooks/check-terraform.py
references:
  - docs/testing.md
---

# The test sits beside the module it tests

Terraform's unit is the module, so the module is what has a test beside it. A reader who opens `modules/network/` finds the module's contract in its variables and outputs, and its behaviour in `modules/network/tests/`, without searching the repository.

Terraform's test framework (Terraform 1.6 and later) already puts it there. `terraform test` runs from the module's directory, discovers files by their `.tftest.hcl` or `.tftest.json` extension, looks in a `tests` directory by default, and always loads test files that sit directly in the module's own directory; HashiCorp recommends not changing the default ([`terraform test`](https://developer.hashicorp.com/terraform/cli/commands/test), [Tests](https://developer.hashicorp.com/terraform/language/tests)). This rule takes the tool's own layout as the convention and requires that it be used. `docs/testing.md` says what the test checks and how it avoids building real infrastructure.

## Conditions

1. **Every reusable module has at least one test file in its own folder or in its `tests/` folder.** Decided by `hooks/check-terraform.py`. A test file is a `.tftest.hcl`, a `.tftest.json`, or an OpenTofu `.tofutest.hcl` (OpenTofu 1.8 and later reads it in preference to the `.tftest.hcl` of the same name, as it does `.tofu` over `.tf`; [What's new in OpenTofu 1.8](https://opentofu.org/docs/v1.8/intro/whats-new/)). A reusable module is a directory under `modules/`, or one another configuration calls by a local path and that declares no backend. A test in another module's folder does not count for this one.

## Where this stops

**Presence, not substance.** A test file with one `run` block that asserts nothing passes. What a test owes the module, an assertion on each output and each validation, is review, and `docs/testing.md` lists it.

**Root configurations are not required to carry a test.** A root configuration composes modules and binds them to one environment; its test is the plan the pipeline posts for review, against the real state (`docs/toolchain.md`). A root that holds resources of its own rather than calling modules is, by `docs/modules.md`, a module that has not been extracted yet.

**`-test-directory` moves the folder, and the hook does not follow it.** A project that changes it gets a finding for every module, which is the rule asking it not to, as HashiCorp does.
