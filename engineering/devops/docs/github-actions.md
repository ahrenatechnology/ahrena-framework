---
id: github-actions
type: doc
clade: engineering
subclade: devops
title: Writing GitHub Actions workflows
summary: How a workflow is structured - triggers, jobs, permissions, timeouts, concurrency - why reusable workflows and composite actions are the units of composition, how pins are kept current, and how caching and matrices are used without opening a door.
references:
  - rules/token-permissions.md
  - rules/action-pinning.md
  - rules/script-injection.md
  - rules/privileged-triggers.md
  - rules/job-timeouts.md
  - docs/tooling.md
---

# Writing GitHub Actions workflows

The companion to five rules: [`token-permissions.md`](../rules/token-permissions.md), [`action-pinning.md`](../rules/action-pinning.md), [`script-injection.md`](../rules/script-injection.md), [`privileged-triggers.md`](../rules/privileged-triggers.md) and [`job-timeouts.md`](../rules/job-timeouts.md). It argues a shape for a workflow file. The syntax is GitHub's, in the [Workflow syntax reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), and is not repeated here.

## A workflow's skeleton

Every workflow this plugin writes opens the same way, because each line closes a default that is unsafe or unbounded:

- **`on:` names the narrowest trigger.** `pull_request` for anything that runs the contributor's code; `push` to the default branch or a tag for what ships; `workflow_dispatch` for a manual action, with typed inputs. `pull_request_target` and `workflow_run` are privileged and only act on results ([`privileged-triggers.md`](../rules/privileged-triggers.md)). A workflow that is required by a merge queue also listens to `merge_group`, without which "status checks will not be triggered" ([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)).
- **`permissions:` at the top is `contents: read`**, or `{}` when the workflow reads nothing, and a job that writes raises only its own scope. Listing one scope sets every other to `none` ([Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)); OpenSSF Scorecard's `Token-Permissions` rewards exactly this shape.
- **Every job has `timeout-minutes`.** The default is 360. Set it to the job's usual duration, read from its last runs, with roughly double for headroom: a 6-minute test job gets 15. The point is that a hang becomes a failure within the time someone is still waiting for the result.
- **`concurrency:` on anything that deploys or publishes**, keyed on the environment or the ref, never cancelling a deploy in flight ([`protected-deployments.md`](../rules/protected-deployments.md)). On a pull-request workflow, `cancel-in-progress: true` keyed on the pull request saves minutes when a new commit lands; that is the one place cancelling is right.

## Composition: reusable workflows and composite actions

Repetition across workflows is factored into one of two units, and the choice follows what is shared.

- **A reusable workflow** (`on: workflow_call`) shares whole jobs: their runners, permissions, environments and secrets. It is the unit for a deploy pipeline used by several services, because the environment and its protection travel with it. Permissions "can only be maintained or reduced — not elevated — throughout the chain", nesting stops at ten levels, a file may call at most 50 unique reusable workflows, and `env` set in the caller does not reach the callee ([Reuse workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows); [Reusing workflow configurations](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)). Pass secrets by name; `secrets: inherit` hands over every secret the caller has, which zizmor `secrets-inherit` reports.
- **A composite action** (`runs: using: composite` in an `action.yml`) shares steps inside one job ([Creating a composite action](https://docs.github.com/en/actions/tutorials/create-actions/create-a-composite-action)). It is the unit for "set up the toolchain and cache", which every job repeats. It has no permissions or secrets of its own: it runs with the calling job's, so its inputs are the only interface and every `run` step declares its `shell`.

A reusable workflow called from another repository is pinned by SHA; a local one (`./.github/workflows/…`) is pinned by the commit that runs it. Both units keep [`script-injection.md`](../rules/script-injection.md): an input is passed to a script through `env:`, never interpolated.

## Keeping pins current

A SHA pin that nobody updates drifts into a known-vulnerable version, and Dependabot "will not create alerts for actions pinned to SHA values" ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)). Version updates still work: configure `package-ecosystem: "github-actions"` with `directory: "/"` ([Keeping your actions up to date with Dependabot](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot)), and Dependabot updates the SHA and the version comment beside it ([changelog, 2022-10-31](https://github.blog/changelog/2022-10-31-dependabot-now-updates-comments-in-github-actions-workflows-referencing-action-versions/)). So a pin is written as `uses: owner/action@<40-hex> # v1.2.3`, and the comment is what Dependabot and a reader use. A repository that adopts the workflow lockfile (`gh actions-lock`, [Workflow dependency lockfiles](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles)) regenerates the lockfile instead and keeps SHA pins only for reusable-workflow calls.

## Caching

A cache is shared state across runs, so it is an input from the past that can be poisoned. GitHub's rules bound it: a run restores caches from its own branch and the default branch (a pull request also from its base), never from a sibling branch ([Dependency caching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)). The same page says "anyone with read access can create a pull request on a repository and access the contents of a cache", so a cache never holds a token or credential. A release or deploy workflow does not restore a cache a pull-request run could have written; zizmor `cache-poisoning` reports the shape. Key a cache on the lock file's hash, so a dependency change is a cache miss.

## Matrices

`strategy.matrix` fans one job out over versions or platforms; `fail-fast` defaults to `true`, which cancels the other legs on the first failure ([Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)). Set `fail-fast: false` when each leg answers a different question (one per operating system, one per cloud) and a reader needs every answer; keep the default when the legs are redundant. A matrix is never the way to deploy to several environments: each environment is its own job, so each has its own approval and concurrency group.

## Runners

GitHub-hosted runners are fresh per job. A self-hosted runner keeps state between jobs, and GitHub says self-hosted runners "should almost never be used for public repositories", because any user can open a pull request that runs on it ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)). Where one is needed for a private network, it is ephemeral, scoped to one repository or runner group, and reached only by jobs that do not run contributor code.

## Where this stops

**Other CI systems** are out of this plugin's scope; the principles carry over, the syntax does not.

**Building and testing the code** is the language plugin's: which test command, which linter. This page says how the job that runs them is shaped.

**Release and deploy stages** are [`delivery-pipeline.md`](delivery-pipeline.md) and [`releases-and-rollback.md`](releases-and-rollback.md).
