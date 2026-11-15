---
id: repository-governance
type: doc
clade: engineering
subclade: devops
title: Repository governance - rulesets, required checks, code owners and the merge queue
summary: How a repository decides what may reach its default branch and who may change the pipeline - rulesets and their layering, the required checks a pipeline must keep stable, CODEOWNERS for the workflow files, and the merge queue with its merge_group trigger.
references:
  - docs/delivery-pipeline.md
  - docs/environments-and-secrets.md
---

# Repository governance

The pipeline is only as strong as the rules on what may change it and what may merge. This page covers the forge settings a DevOps reader configures and reviews; they live in the forge, not in the tree, and a review reads them with `gh api`.

## Rulesets

A ruleset is a named set of rules on branches or tags. Several can apply at once, there is no priority between them, and they combine with classic branch protection, the most restrictive version of a rule winning; "anyone with read access to a repository can view its active rulesets" ([About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)). That visibility is why rulesets are the place for governance: a contributor can see what their pull request must pass.

The rules that matter for delivery ([Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)):

- **Require a pull request before merging**, with approvals and code-owner review. The approval is the gate a private repository on Pro or Team uses in place of an environment reviewer ([`environments-and-secrets.md`](environments-and-secrets.md)).
- **Require status checks to pass**, naming the jobs of the verify stage.
- **Block force pushes** and **restrict deletions** on the default branch and on release tags, so history and what was deployed cannot be rewritten.
- **Require deployments to succeed before merging**, which makes a staging deploy a precondition of the merge.
- **Require signed commits**, so "contributors and bots can only push commits that have been signed and verified".
- **Require code scanning results**, where the project runs code scanning.

"Require merge queue" and "Require workflows to pass before merging" appear only in the Enterprise Cloud version of the page; on other plans, the merge queue is set on the branch, and an organisation-wide required workflow is not available.

## Required checks a pipeline must keep stable

A required check is named by its job name. Renaming a job, or moving it into a matrix (whose legs are named `job (value)`), leaves the old name required and never reported, and every pull request waits forever. A change to a workflow that holds a required check therefore names the check it keeps, and a review reads the ruleset beside the diff. A check that only runs on some paths (`paths:` filter) and is required blocks every pull request that does not touch those paths; the usual fix is a job that always runs and decides inside.

## CODEOWNERS for the pipeline

`CODEOWNERS` is read from `.github/`, the root or `docs/`, "in that order", the "last matching pattern takes the most precedence", owners need write access, and the file must be on the base branch of the pull request ([About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)). A line giving `/.github/` to the team that owns delivery, with code-owner review required by the ruleset, means a change to a workflow, an action or `CODEOWNERS` itself cannot merge without them. Because the last match wins, that line goes at the end of the file, after any broad pattern.

## The merge queue

A merge queue merges pull requests one group at a time, after re-running the checks on the result of merging them onto the latest base. A workflow that provides a required check "must use the `merge_group` event" ([Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)), and the event alone is not enough: the job must run on it, so a `paths:` filter or an `if:` that skips on `merge_group` stalls the queue. A queue is worth it when the default branch breaks because two green pull requests conflict in behaviour; on a repository with few merges a day it adds minutes for nothing.

## Where this stops

**Organisation policy** (allowed actions, the default token permissions, the SHA-pinning requirement, fork approval) is set above the repository; [`github-actions.md`](github-actions.md) names the settings that touch a workflow, and the organisation's owners decide them.

**Who should be a code owner or a reviewer** is the team's decision, not a rule here.
