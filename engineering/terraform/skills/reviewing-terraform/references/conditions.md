# Terraform review conditions

Each condition cites the numbered rule condition it applies and says who decides it: `hook` means `hooks/check-terraform.py` prints it and the reviewer reports it as printed; `review` means a reader decides it here.

**Severity is never a property of the condition.** It follows the tests of `ahrena-engineering-quality:docs/review-findings.md`: blocking when the violating line is one this change introduces or edits; deferrable when the line, or the fix, is outside the diff; question when deciding needs an input only the author or the organisation holds; unchecked when nothing could decide it. A condition below that is gated by the abstraction trigger of `yagni.md` is a question by that document's own rule, and says so.

**One line, one finding.** When a line violates more than one condition (an output that carries a policy is TF-7 and, with no consumer, TF-10), write one finding that cites every condition it violates. A credential under a name the hook does not recognise is the baseline secrets discipline's `SEC-n` finding, routed on every change, and is not repeated here.

## State

- **TF-1** (hook) — `rules/state.md` 1. A state file, a backup, a `*.tfplan` or a `.terraform/` directory is in the change. Correction: remove it from the index and add the pattern to `.gitignore`. A state file that reached a commit stays in history, so every secret it held is rotated.
- **TF-2** (hook) — `rules/state.md` 2. A root configuration with no backend, or on `backend "local"`. Correction: declare the remote backend the other roots use, partially, with credentials from the environment.
- **TF-3** (hook) — `rules/state.md` 3. `-lock=false` in a script or pipeline. Correction: delete the flag; a stale lock is released by its owner with `force-unlock`, never bypassed.
- **TF-4** (review) — `rules/state.md` 4. The backend does not lock, or does not encrypt at rest, or its credentials sit in the block or on a `-backend-config` command line. Read the backend's settings against its documentation; locking and encryption are opt-in on some backends. When the settings arrive at `init` and nothing in the repository shows them, the condition is unchecked, with that reason. Correction: name the setting to turn on, or move the credential to the environment.
- **TF-5** (review) — `rules/state.md` 5. Two environments share a backend configuration, or are separated only by CLI workspaces. Correction: a root configuration per environment, each with its own backend and credentials.

## Secrets

- **TF-6** (hook) — `rules/secrets.md` 1 to 4. A secret-named variable with a default or not marked sensitive, a secret-named argument given a literal, or a versioned `.tfvars` giving one a literal. Correction: no default, `sensitive = true` (or `ephemeral = true`), the value from `TF_VAR_<name>` or an ephemeral resource. A literal that reached a commit is rotated.

## Outputs and exposure

These are the Terraform form of the exposure rule, [`layer-exposure.md`](../../../../security/rules/layer-exposure.md): what a configuration emits is an allowlist.

- **TF-7** (hook) — `rules/outputs.md` 1. An output that carries a policy, a credential or a connection string, by its name, its value or the attribute it references, is not marked `sensitive = true`. Correction: stop exporting it and let the consumer read the value from where it is stored, or, where a consumer needs it from this output, mark it.
- **TF-8** (hook) — `rules/outputs.md` 2. A root output exports a whole resource or module object. Correction: export the named attributes a consumer reads.
- **TF-9** (hook) — `rules/outputs.md` 3. A pipeline or script prints `terraform output -json` or `-raw`, or `terraform show -json`, to its log, with or without global options such as `-chdir`. Correction: redirect to a file the job keeps private, or capture the one value the next step needs.
- **TF-10** (review) — `rules/outputs.md` 4. An output that describes access or topology (a role, a policy, an account id, a subnet layout, an internal hostname) with no consumer the change or the repository names. When the consumer may exist outside the repository, it is a question to the author. Correction: delete it, or name the consumer; where the consumer is another configuration, publish the one value to a separate store instead of exposing the state through `terraform_remote_state`.
- **TF-11** (review) — `rules/outputs.md` 5. A `validation`, `precondition`, `postcondition`, `check` or test `error_message` that interpolates a sensitive value or a whole object. Correction: name the rule that failed, not the value.

## Pinning

- **TF-12** (hook) — `rules/pinning.md` 1 to 5. No `required_version`; a provider used and not declared, or declared with no version; a root with no upper bound or a reusable module with one; a registry module without an exact version or a git module without a tag or commit; a root whose lock file is missing or does not record a declared provider. Correction as the hook says.

## Module boundaries

- **TF-13** (hook) — `rules/module-boundaries.md` 1 to 3. A cycle in local module calls, a call into a root configuration, a provider block or a backend in a reusable module. Correction as the hook says.
- **TF-14** (review) — [`solid.md`](../../../../fundamentals/rules/solid.md) condition 6, in the form `docs/modules.md` gives it for Terraform: the root is the only place concrete objects are chosen. A reusable module creates or looks up an object it should receive as a variable (a network, a key, a zone). Correction: take its id or name as a variable and let the root pass it.
- **TF-15** (review) — [`kiss.md`](../../../../fundamentals/rules/kiss.md) condition 2, in HCL: a boolean variable whose value selects between two shapes of the module (adds or removes a group of resources through `count` or a conditional). Correction: two modules, or the caller passes in what should exist.
- **TF-16** (review, question) — [`yagni.md`](../../../../fundamentals/rules/yagni.md) condition 1: a new reusable module that wraps one resource, or has one caller. Gated by the abstraction trigger, so it is a question: which second consumer, or which test, needs the seam? If none, the resource goes inline in the root.

## Tests

- **TF-17** (hook) — `rules/test-placement.md` 1. A reusable module with no test beside it. Correction: a `.tftest.hcl` in its folder or its `tests/`.

## Drift and change

- **TF-18** (review) — `rules/drift.md` 4. A resource address renamed without a `moved` block, an object adopted without an `import` block, or one dropped from code without a `removed` block, so the plan destroys or recreates something the author meant to keep. Read the posted plan for `must be replaced` and `destroy`, or the base revision when no plan is posted. Correction: the block that says what was meant.
- **TF-19** (review) — `rules/drift.md` 6. `lifecycle { ignore_changes = all }`, or an `ignore_changes` list with no comment pointing at the issue that names the system owning those attributes. Correction: name the attributes another system legitimately owns, and only those, with the pointer.
- **TF-20** (review, question) — `rules/drift.md` 3. The change reconciles a change made outside code. Ask which: was it wanted (code edited to match, refresh-only apply), or is the apply meant to revert it?
