---
id: token-permissions
type: rule
clade: engineering
subclade: devops
title: Every workflow declares the least GITHUB_TOKEN permissions it uses
statement: A workflow declares permissions at the top or on every job, never write-all or read-all, and a job holds only the write scopes its steps use.
enforcement: judgment
references:
  - docs/github-actions.md
---

# Every workflow declares the least GITHUB_TOKEN permissions it uses

A job that declares no `permissions` runs with the repository's or organisation's default for `GITHUB_TOKEN`, and the permissive default grants read and write to every scope ([Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)). The workflow file does not say which default applies, so a reader cannot tell what a compromised step could do. Once any scope is listed, every scope not listed is set to `none` ([Workflow syntax, `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)), which turns the block into an allowlist. GitHub's own guidance is to grant the token the minimum it needs ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)). [`docs/github-actions.md`](../docs/github-actions.md) argues the shape: read at the top, writes on the job that needs them.

## Conditions

1. **The workflow declares `permissions` at the top level, or every job declares its own.** Decided by `hooks/check-workflows.py`, which reports each job left on the default. A job that calls a reusable workflow counts: its block caps what the called workflow can hold, because permissions "can only be maintained or reduced" down the chain ([Reuse workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)). Also reported by zizmor `excessive-permissions` and OpenSSF Scorecard `Token-Permissions`.
2. **No workflow or job grants `write-all` or `read-all`.** Decided by `hooks/check-workflows.py`. Both shorthands grant every scope, including ones added after the file was written. `permissions: {}` is the form for a job that needs none.
3. **Every write scope a job holds is one its steps use.** `contents: write` for a job that pushes a tag, `id-token: write` for a job that federates to a cloud, `pull-requests: write` for a job that comments. Decided by review, reading each write scope against the steps; zizmor `excessive-permissions` reports the common over-grants.

## Where this stops

**The hook reads the file, not the forge.** Whether the organisation's default is restricted is a setting; a file that declares nothing is reported whatever that setting is, because the file must not depend on it.

**Read scopes are not weighed.** A job that lists `issues: read` it never uses passes condition 3. Excess read on the repository's own data is a smaller risk than excess write, and chasing it costs more review than it saves.

**A composite action has no permissions of its own.** It runs with the token of the job that calls it, so the job's block is the one that counts.

**This rule declares judgment because condition 3 needs a reader.** `hooks/check-workflows.py` decides conditions 1 and 2 exactly, and its tests pin each; the statement reaches the agent's instruction file so the rest is read.
