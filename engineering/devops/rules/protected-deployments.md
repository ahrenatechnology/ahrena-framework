---
id: protected-deployments
type: rule
clade: engineering
subclade: devops
title: A deploy to a protected environment is approved, serialised and reversible
statement: A deploy job names its environment, holds a concurrency group that queues, needs a reviewer where the plan allows, and has a stated rollback.
enforcement: judgment
references:
  - docs/environments-and-secrets.md
  - docs/releases-and-rollback.md
---

# A deploy to a protected environment is approved, serialised and reversible

An environment is where GitHub attaches the controls a deploy needs: required reviewers, a wait timer, the branches allowed to deploy, and secrets a job cannot read "until one of the required reviewers approves it" ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)). Two runs deploying to the same environment at once race; a concurrency group keeps "at most one running job or workflow" in the group ([Workflow syntax, `concurrency`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)). A deploy with no way back turns a bad release into an outage. A protected environment is production and any environment the project names as one; [`docs/environments-and-secrets.md`](../docs/environments-and-secrets.md) argues the controls and [`docs/releases-and-rollback.md`](../docs/releases-and-rollback.md) the rollback.

## Conditions

1. **A job that names an environment holds a concurrency group**, its own or the workflow's. Decided by `hooks/check-workflows.py`, for every environment: two deploys to staging race as surely as two to production.
2. **A deploy's concurrency group does not set `cancel-in-progress: true`.** Cancelling a deploy halfway leaves the environment between two versions, and an interrupted `terraform apply` leaves its state locked. A newer run waits; the `queue` key decides how many wait. Decided by `hooks/check-workflows.py`.
3. **A protected environment requires a reviewer, with self-review prevented, where the repository's plan offers required reviewers.** GitHub offers them on public repositories on every plan; on Free, Pro and Team plans a private repository does not get them ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)). There, the environment restricts deployment to protected branches, and the branch's ruleset requires an approved pull request, so the merge is the approval; the workflow says so in a comment on the job. Decided from the forge by `reviewing-pipelines`, which reads the environment's protection rules with `gh api`; unchecked without a token.
4. **The deploy has a stated rollback.** A workflow input or a job that redeploys a named earlier version, a reverse migration, a feature flag to turn off, or a runbook the workflow links; and what the rollback cannot undo is named. Decided by review.
5. **A protected environment's secrets and cloud trust are scoped to it.** Secrets that reach production are environment secrets, not repository secrets, and the cloud's federation trusts the environment's subject (`repo:ORG/REPO:environment:NAME`). Decided by review, with the cloud plugin for the trust side.

## Where this stops

**The hook reads the file, not the environment.** Whether `production` has reviewers is in the forge's settings; condition 3 needs a token, and a review without one reports it unchecked rather than passed.

**A job without `environment:` is not a deploy to this rule**, even if it calls a cloud. That is a finding of review under condition 5 when it touches a protected target: the environment is how the controls attach.

**Rollback is stated, not rehearsed.** Whether it works is tested by the project; the rule asks that the way back exists and is written down before the deploy runs.
