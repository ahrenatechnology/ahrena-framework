---
id: job-timeouts
type: rule
clade: engineering
subclade: devops
title: Every job has a timeout
statement: Every job that runs steps declares timeout-minutes, so a hung step fails in minutes rather than holding a runner for six hours.
enforcement: hook
enforced-by: hooks/check-workflows.py
references:
  - docs/github-actions.md
---

# Every job has a timeout

A job without `timeout-minutes` runs until GitHub's default, which is 360 minutes ([Workflow syntax, `jobs.<job_id>.timeout-minutes`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)). A hung test, a prompt waiting for input or a lock that never releases then holds a runner, and a concurrency group behind it, for six hours, and on a paid runner bills for them. A timeout a little above the job's normal duration turns the hang into a failure someone sees. [`docs/github-actions.md`](../docs/github-actions.md) says how to set the number.

## Conditions

1. **Every job that runs steps declares `timeout-minutes`.** A literal or an expression. Decided by `hooks/check-workflows.py`. Neither actionlint nor zizmor reports a missing timeout, which is why the hook does.

## Where this stops

**A job that calls a reusable workflow is exempt**: the caller cannot set `timeout-minutes`, and the called workflow's jobs carry their own.

**The number is not judged.** A timeout of 360 passes, as does one of 5 on a job that needs 20. The doc gives the measure: the job's recent duration with headroom.

**Step-level timeouts are optional.** One step that can hang inside a long job is worth its own; the rule asks only for the job's.
