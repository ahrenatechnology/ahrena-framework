---
id: action-pinning
type: rule
clade: engineering
subclade: devops
title: A third-party action runs from an immutable reference
statement: A third-party action is pinned to a full commit SHA or locked in the workflow lockfile, a reusable workflow to a full SHA, a container image by digest.
enforcement: judgment
references:
  - docs/github-actions.md
  - docs/tooling.md
---

# A third-party action runs from an immutable reference

A tag or a branch is a pointer the action's owner, or whoever takes over their account, can move. GitHub's [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) says a tag "can be moved or deleted if a bad actor gains access to the repository storing the action", and tells the reader to pin to a commit SHA "to mitigate the risk of a bad actor adding a backdoor". The same page now names a stronger measure: a workflow dependency lockfile, `.github/workflows/actions.lock`, which "supersedes SHA pinning for repositories that adopt it" and covers transitive dependencies, except those of reusable workflow calls ([Workflow dependency lockfiles](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles)). [`docs/github-actions.md`](../docs/github-actions.md) says how a pin is kept current; [`docs/tooling.md`](../docs/tooling.md) names the tools.

## Conditions

1. **A third-party action is pinned to a full-length commit SHA, or the repository carries the workflow lockfile, and a reusable workflow from another repository is pinned to a full-length SHA.** Third-party means an owner other than `actions` and `github`. A step's `uses:` passes on a tag when `.github/workflows/actions.lock` exists, because GitHub refuses at run time an action the lockfile does not list; a job's `uses:` that calls a reusable workflow does not, because the lockfile does not cover it. Decided by `hooks/check-workflows.py`, in workflows and in composite actions. Also reported by zizmor `unpinned-uses` and Scorecard `Pinned-Dependencies`; actionlint does not check pinning.
2. **A `docker://` action names its image by digest (`@sha256:`).** A tag on a registry is as mutable as a tag on a repository. Decided by `hooks/check-workflows.py`; zizmor `unpinned-images` reports the same for job containers.
3. **The pinned SHA is a commit of the action's own repository and matches the release named beside it.** GitHub tells the reader to verify the SHA "is from the action's repository and not a repository fork" ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)). Decided by zizmor `impostor-commit` and `ref-version-mismatch` where the project runs it, otherwise by review.

## Where this stops

**GitHub-owned actions are outside condition 1.** `actions/*` and `github/*` are published by the platform that runs the workflow; a repository that wants them pinned too turns on the organisation policy "Require actions to be pinned to a full-length commit SHA", which applies to GitHub-authored actions as well ([Managing GitHub Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)), or runs zizmor, whose default policy hash-pins every action.

**A local action (`./…`) is pinned by the commit that runs it**, and an expression in `uses:` is not read.

**A pin is not a review of the action.** Pinning stops the reference from moving; whether the action at that commit is safe to run is `reviewing-supply-chain`'s question (SUP-4 and the rest).

**This rule declares judgment because condition 3 needs a reader.** `hooks/check-workflows.py` decides conditions 1 and 2 exactly, and its tests pin each; the statement reaches the agent's instruction file so the rest is read.
