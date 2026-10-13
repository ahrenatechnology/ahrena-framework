---
name: issue-cost
description: Report what an issue, or every issue of a repository, cost to build in tokens, hours and money.
type: command
clade: costs
argument-hint: "[issue number] [owner/name]"
references:
  - skills/reporting-issue-costs/SKILL.md
---

# /issue-cost

Invoke `reporting-issue-costs` with the arguments below.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| issue number | no | The issue to report. Without it, every issue of the repository is reported |
| `owner/name` | no | The repository. Without it, the one the current directory is a clone of |

## What runs

`skills/reporting-issue-costs`, from step 1.
