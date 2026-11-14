# Terraform review conditions

Each condition names its source rule and who decides it: `hook` means `hooks/check-terraform.py` prints it and the reviewer reports it as printed; `review` means a reader decides it here. Severity is the default; a reviewer who lowers one says why.

## State

- **TF-1** (hook, blocking) — `rules/state.md` 1. A state file, a backup, a `*.tfplan` or a `.terraform/` directory is in the change. Correction: remove it from the index and add the pattern to `.gitignore`. A state file that reached a commit stays in history, so every secret it held is rotated.
- **TF-2** (hook, blocking) — `rules/state.md` 2. A root configuration with no backend, or on `backend "local"`. Correction: declare the remote backend the other roots use, partially, with credentials from the environment.
- **TF-3** (hook, blocking) — `rules/state.md` 3. `-lock=false` in a script or pipeline. Correction: delete the flag; a stale lock is released by its owner with `force-unlock`, never bypassed.
- **TF-4** (review, blocking) — `rules/state.md` 4. The backend does not lock, or does not encrypt at rest, or its credentials sit in the block or on a `-backend-config` command line. Read the backend's own settings against its documentation; locking and encryption are opt-in on some backends. Correction: name the setting to turn on, or move the credential to the environment.
- **TF-5** (review, blocking) — `rules/state.md` 5. Two environments share a backend configuration, or are separated only by CLI workspaces. Correction: a root configuration per environment, each with its own backend and credentials.

## Secrets

- **TF-6** (hook, blocking) — `rules/secrets.md` 1 to 4. A secret-named variable with a default or not marked sensitive, a secret-named argument given a literal, or a versioned `.tfvars` giving one a literal. Correction: no default, `sensitive = true` (or `ephemeral = true`), the value from `TF_VAR_<name>` or an ephemeral resource. A literal that reached a commit is rotated.
- **TF-7** (review, blocking) — `rules/secrets.md`, beyond its names. A secret under a name the hook does not recognise, a credential built into a string, a generated secret written to an output or a file. Correction as TF-6, and a write-only argument where the provider has one.

## Outputs and exposure

These are the Terraform form of the exposure rule of issue #294: what a configuration emits is an allowlist.

- **TF-8** (hook, blocking) — `rules/outputs.md` 1. An output that carries a policy, a credential or a connection string, by its name, its value or the attribute it references, is not marked `sensitive = true`. Correction: mark it, or, better, stop exporting it and let the consumer read the value from where it is stored.
- **TF-9** (hook, blocking) — `rules/outputs.md` 2. A root output exports a whole resource or module object. Correction: export the named attributes a consumer reads.
- **TF-10** (hook, blocking) — `rules/outputs.md` 3. A pipeline or script prints `terraform output -json` or `-raw`, or `terraform show -json`, to its log. Correction: redirect to a file the job keeps private, or capture the one value the next step needs.
- **TF-11** (review, blocking when the value is a policy, a credential or account-locating; deferrable otherwise) — `rules/outputs.md` 4. An output that describes access or topology (a role, a policy, an account id, a subnet layout, an internal hostname) with no consumer the change or the repository names. Correction: delete it, or name the consumer; where the consumer is another configuration, publish the one value to a separate store instead of exposing the state through `terraform_remote_state`.
- **TF-12** (review, deferrable) — `rules/outputs.md`. A `validation`, `precondition`, `postcondition` or test `error_message` that interpolates a sensitive value or a whole object. Correction: name the rule that failed, not the value.

## Pinning

- **TF-13** (hook, blocking) — `rules/pinning.md` 1 to 5. No `required_version`; a provider used and not declared, or declared with no version; a root with no upper bound or a reusable module with one; a registry module without an exact version or a git module without a tag or commit; a root with no `.terraform.lock.hcl`. Correction as the hook says.
- **TF-14** (review, deferrable) — `rules/pinning.md`. A lock file changed with no change to the constraints that would explain it, or a provider's major version moved inside this change without a word in the description. Correction: say why in the description, or revert the lock file.

## Module boundaries

- **TF-15** (hook, blocking) — `rules/module-boundaries.md` 1 to 3. A cycle in local module calls, a call into a root configuration, a provider block or a backend in a reusable module. Correction as the hook says.
- **TF-16** (review, deferrable) — `docs/modules.md`. A module that creates or looks up what it should receive as a variable; a variable that takes a whole object to read two attributes; a boolean variable that switches the module between two shapes; a module that wraps one resource. Correction: take the dependency as an input, take the attributes, split the module, inline the resource.
- **TF-17** (review, deferrable) — `docs/modules.md`. An existing module edited for one caller's case. Correction: a new module that calls it, or a new variable whose default keeps today's behaviour.

## Tests

- **TF-18** (hook, blocking) — `rules/test-placement.md` 1. A reusable module with no test beside it. Correction: a `.tftest.hcl` in its folder or its `tests/`.
- **TF-19** (review, deferrable) — `docs/testing.md`. A test that applies real infrastructure where `command = plan` or a mock would do, or that does not cover a new output, a new validation or a new branch. Correction: name the missing `run` block.

## Drift and change

- **TF-20** (review, blocking) — `rules/drift.md` 4. A resource address renamed without a `moved` block, an object adopted without an `import` block, or one dropped from code without a `removed` block, so the plan destroys or recreates something the author meant to keep. Read the posted plan for `must be replaced` and `destroy`. Correction: the block that says what was meant.
- **TF-21** (review, deferrable) — `rules/drift.md` 3. `lifecycle { ignore_changes = all }`, or an `ignore_changes` with no comment pointing at the issue that explains it. Correction: name the attributes another system legitimately owns, and only those.
- **TF-22** (review, question) — `rules/drift.md` 3. The change reconciles a change made outside code. Ask which: was it wanted (code edited to match, refresh-only apply), or is the apply meant to revert it?
