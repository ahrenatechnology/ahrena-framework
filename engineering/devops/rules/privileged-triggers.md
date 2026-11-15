---
id: privileged-triggers
type: rule
clade: engineering
subclade: devops
title: A privileged trigger never runs the contributor's code
statement: A pull_request_target or workflow_run workflow never checks out or runs the contributor's code in a job that has secrets or a write token in reach.
enforcement: judgment
references:
  - docs/github-actions.md
---

# A privileged trigger never runs the contributor's code

A `pull_request` workflow from a fork receives no secrets other than `GITHUB_TOKEN`, and that token is read-only ([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)). `pull_request_target` is the opposite: it "runs in the context of the default branch of the base repository", with its secrets and token, and the same page warns that "running untrusted code on the `pull_request_target` trigger may lead to security vulnerabilities". `workflow_run` "is able to access secrets and write tokens" even when the workflow that triggered it could not. The [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) says not to check out untrusted code in either. This is the pipeline form of SUP-4 of `reviewing-supply-chain`.

## Conditions

1. **No job of a `pull_request_target` or `workflow_run` workflow checks out the contributor's code.** `actions/checkout` with a `ref` or `repository` naming the pull request head (`github.event.pull_request.head.sha`, `.head.ref`, `.head.repo.full_name`, `github.head_ref`, `refs/pull/…`) or the triggering run's head (`github.event.workflow_run.head_sha`, `.head_branch`), and a `run:` that does `gh pr checkout` or fetches those refs. Decided by `hooks/check-workflows.py`. Also reported by zizmor `dangerous-triggers` and `dangerous-checkout`, and by Scorecard `Dangerous-Workflow`.
2. **A `workflow_run` workflow that downloads an artifact of the triggering run treats it as data.** It does not execute it, source it, write it to `GITHUB_ENV` or `GITHUB_PATH`, or interpolate it into a script. Decided by review, with zizmor `github-env`.
3. **Work that needs the contributor's code and a secret is split.** The unprivileged `pull_request` workflow builds and tests; a privileged workflow acts only on its result, which the [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) names as the use of `workflow_run`. Decided by review.
4. **A release or deploy workflow does not restore a cache that a pull-request run can write, and a job that uploads its workspace does not keep the checkout's token on disk.** "Anyone with read access can create a pull request on a repository and access the contents of a cache" ([Dependency caching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)), so a pull request can seed what a privileged run restores; and `actions/checkout` persists its token in the workspace unless `persist-credentials: false`. Decided by review, with zizmor `cache-poisoning` and `artipacked`.
5. **No job that a fork's pull request triggers runs on a self-hosted runner of a public repository.** GitHub says self-hosted runners "should almost never be used for public repositories", because any user can open a pull request that runs on them ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)). Decided by review, with zizmor `self-hosted-runner`.

## Where this stops

**Checking out the base is the safe use of the trigger.** A labeller or a commenter that reads the pull request through the API and checks out nothing passes.

**`issue_comment` and other triggers that run with secrets** are read by review under condition 3, and zizmor `dangerous-triggers` lists them.

**A self-hosted runner on a private repository**, reached only by members, is outside condition 5; `docs/github-actions.md` says how to scope one.

**This rule declares judgment because conditions 2 to 5 need a reader.** `hooks/check-workflows.py` decides condition 1 exactly, and its tests pin each; the statement reaches the agent's instruction file so the rest is read.
