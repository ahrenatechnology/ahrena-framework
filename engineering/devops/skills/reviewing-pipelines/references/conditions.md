# Pipeline review conditions

Each condition is identified as `PIPE-n`. A finding cites the identifier, the file and the line. **Decided by** says whether the hook (`hooks/check-workflows.py`), the forge (`gh api`) or the reviewer decides it. Conditions decided by the hook are listed so the reader knows they were covered; the reviewer does not re-derive them, it reports the hook's output.

## Token and triggers

### PIPE-1 Permissions declared, no shorthand
- **Decided by:** hook, `token-permissions` 1 and 2.
- **Correct:** `permissions: contents: read` at the top; each job raises only its write scope.

### PIPE-2 A write scope the job does not use
- **Decided by:** reviewer, `token-permissions` 3.
- **Detect:** for each `write` scope, find the step that uses it: a push, a tag, a release, a comment, a package publish, `id-token` for a cloud login. No step, finding.
- **Correct:** drop the scope, or move it to the one job that uses it.

### PIPE-3 Privileged trigger runs contributor code
- **Decided by:** hook for the checkout, `privileged-triggers` 1; reviewer for artifacts and split, 2 and 3.
- **Detect:** on `pull_request_target`, `workflow_run`, `issue_comment`: a downloaded artifact that is executed, sourced, or written to `GITHUB_ENV`/`GITHUB_PATH`; a build of the head in the same job as a secret.
- **Correct:** build and test in an unprivileged `pull_request` workflow; act on its result only.

### PIPE-4 Untrusted text in a script
- **Decided by:** hook for the listed contexts, `script-injection` 1; reviewer for other paths, 2.
- **Detect:** a step output, a `workflow_dispatch` input, an artifact's content, derived from contributor text and interpolated into `run:`.
- **Correct:** pass it through `env:` and quote it.

## Supply chain of the workflow

### PIPE-5 Mutable action reference
- **Decided by:** hook, `action-pinning` 1 and 2.
- **Correct:** `owner/action@<40-hex> # vX.Y.Z`, or the lockfile; a reusable workflow by SHA.

### PIPE-6 A pin that is not what it says
- **Decided by:** zizmor `impostor-commit`, `ref-version-mismatch` when present; otherwise the reviewer, `action-pinning` 3.
- **Detect:** a SHA changed in the diff whose version comment did not change, or the reverse; a SHA not on the action's repository (`gh api repos/OWNER/REPO/commits/SHA` returns 404 or a fork).

### PIPE-7 Cache poisoning and persisted credentials
- **Decided by:** reviewer, `privileged-triggers` 4, with zizmor `cache-poisoning` and `artipacked`.
- **Detect:** a release or deploy workflow restoring a cache a pull-request run writes; `actions/checkout` leaving its token on disk (`persist-credentials` not `false`) in a job that uploads the workspace as an artifact.

## Cloud credentials

### PIPE-8 Long-lived cloud key
- **Decided by:** hook, `cloud-credentials` 1 to 3.
- **Correct:** `docs/cloud-authentication.md`, the cloud's section.

### PIPE-9 Federation not scoped to the repository and environment
- **Decided by:** reviewer, `cloud-credentials` 4, with the cloud plugin's review skill.
- **Detect:** in the change or the repository's IaC: an AWS trust policy whose `sub` is `repo:ORG/*`; a Google Cloud provider whose attribute condition names only an owner for a deploy identity; an Azure federated credential on a branch subject for a production identity. A deploy job with `id-token: write` and no `environment:`.

## Log exposure

### PIPE-10 Secret, environment, trace, token or debug log printed
- **Decided by:** hook, `log-exposure` 1 to 5; Terraform JSON plan and outputs by the Terraform hook, `outputs` 3.
- **Correct:** pipe or redirect the secret, drop the dump, drop `-x` in jobs with secrets, capture and `::add-mask::` a minted token, `TF_LOG` off.

### PIPE-11 Anything else sensitive reaching the log, a summary, a comment or an artifact
- **Decided by:** reviewer, `log-exposure` 6 and `ahrena-engineering-security:rules/layer-exposure.md` condition 4.
- **Detect:** a step that prints a deploy tool's whole output (resource IDs, ARNs, connection strings); a plan file, state or `.env` uploaded with `actions/upload-artifact` on a public repository or with no `retention-days`; a plan or error posted to a pull request comment on a public repository with values the plan does not redact; a script called by the step that runs with `--verbose`/`--debug`; `ACTIONS_STEP_DEBUG` or `ACTIONS_RUNNER_DEBUG` set as a repository secret or variable (`gh variable list`; a secret's name is visible with `gh secret list`).
- **Correct:** print named fields; keep the artifact private and short-lived, or pass it by a private store; post the human-readable plan only as the Terraform plugin allows.

## Deployments

### PIPE-12 Deploy without a concurrency guard, or cancelling in flight
- **Decided by:** hook, `protected-deployments` 1 and 2.

### PIPE-13 Protected environment without a required reviewer
- **Decided by:** forge, `protected-deployments` 3. `gh api repos/OWNER/REPO/environments/NAME` and read `protection_rules` for `required_reviewers` (with `prevent_self_review`) and `deployment_branch_policy`. Where the plan offers no reviewers, read the ruleset of the deploying branch for a required approval, and the job's comment saying so.
- **Unchecked:** without a token, or for an environment the workflow creates on first use.

### PIPE-14 No stated rollback
- **Decided by:** reviewer, `protected-deployments` 4.
- **Detect:** a deploy job to a protected environment with no input or job that redeploys a named version, no linked runbook, and no statement of what cannot be undone, in the workflow or in the docs it links.

### PIPE-15 Production secret or trust not scoped to the environment
- **Decided by:** reviewer, `protected-deployments` 5.
- **Detect:** a production credential read from `secrets.` in a job without `environment:`; a repository secret where an environment secret serves.

## Operations of the pipeline itself

### PIPE-16 Job without a timeout
- **Decided by:** hook, `job-timeouts` 1.

### PIPE-17 A required check renamed or skipped
- **Decided by:** reviewer, with the ruleset (`gh api repos/OWNER/REPO/rules/branches/BRANCH`). No rule of this plugin holds it, because the ruleset lives in the forge: a finding here is a question when the ruleset cannot be read, and deferrable otherwise, citing `docs/repository-governance.md`, never blocking.
- **Detect:** a job renamed, matrixed or `paths:`-filtered whose name a ruleset requires; a required workflow that does not run on `merge_group` when a merge queue is on.

### PIPE-18 Self-hosted runner reachable by contributor code
- **Decided by:** reviewer, `privileged-triggers` 5, with zizmor `self-hosted-runner`.
- **Detect:** `runs-on: self-hosted` (or a self-hosted label) in a workflow a fork's pull request triggers, on a public repository.
