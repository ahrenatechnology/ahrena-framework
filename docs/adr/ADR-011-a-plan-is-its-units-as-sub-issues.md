# ADR-011: A plan is its units, as sub-issues in order

- **Status:** accepted
- **Date:** 2026-09-28
- **Issue:** #93
- **Supersedes:** ADR-004

## Context

`ADR-004` made the plan an artifact on GitHub rather than a row in
`ROADMAP.md`, which is what the owner chose on #45: issue, plan sub-issue,
pull request. It then described that plan as a single sub-issue whose body
lists every unit, its order, what each touches and what blocks what.

That reading does not match the model the owner chose, and the evidence says
so from three sides.

- **The predecessor.** `kata-decompose-issue-into-plans` created one plan
  sub-issue per unit, each becoming one pull request. Its one refused part,
  the local cache of plan text, is refused here too and stays refused.
- **This repository's practice.** Every plan made since #45 was surveyed has
  been units as sub-issues. #45 was decomposed into #91 to #96, and #92 into
  #98, #99 and #100, each one pull request. No single-plan sub-issue was ever
  written, and nobody missed one.
- **The forge.** GitHub has native sub-issues, and native issue dependencies:
  `blockedBy` and `blocking`, with a REST endpoint to set them. A body listing
  units and their order would restate what the sub-issues and their
  dependencies already record, and it would drift from them.

The owner's direction on #104 also applies. Where the forge provides a
capability, the framework uses it, and where the forge does not, the
framework does the work itself.

## Decision

A plan is the issue it plans, its units as sub-issues, and the order between
them as the forge's native dependencies.

Each unit is one sub-issue, answered by one pull request, and holds the
acceptance criteria that pull request must meet (`ADR-007`). The order is
`blocked by`, set on the forge, not written in prose. The parent's body
carries a `## Plan` section with what no list of sub-issues can hold: the
strategy the change was split by, why, and whether the units stack.

Where the forge has no native sub-issues or dependencies, the `## Plan`
section holds the units and their order too, and the agent keeps it current.

The whole decomposition is confirmed by a person before the first unit is
created, which is gate 1 (`ADR-009`) applied to a plan.

## Consequences

`contributing/rules/planning.md` and `hooks/check-plan.py` hold two
properties of a plan that a script can decide. A pull request does not close
an issue whose sub-issues are still open. #45 was closed with its work still
open twice, once through a linked branch and once through a commit message;
this catches the same outcome whenever a pull request causes it, through its
body or through a linked branch. A commit message is protected-trunk's to stop. And it does not close an issue blocked by an open one,
unless it is a layer of a stack, whose order the stack already holds.

`skills/planning-changes` owns the decomposition checklist that
`stacked-pull-requests.md` and `ADR-006` deferred. The predecessor built that
checklist twice, for plans and for stacks, and the two copies drifted. Here
there is one.

A plan now costs one issue per unit, and no issue for the plan itself. The
parent already exists. The price is that the plan's rationale lives in the
parent's body, which can be edited, and the forge's edit history is its only
record, the same trade `ADR-007` made for acceptance criteria.

The size #45 gave for Group 5 under the old reading, about 350 lines, was for
a plan sub-issue with its own shape and rule. This reading needs less,
because the forge carries the structure.

`ADR-004` stays in the log, superseded. Its choice of GitHub over
`ROADMAP.md`, and its refusal of the cached plan, both stand. What is
superseded is its reading of "plan sub-issue" as one document.

## Alternatives considered

- **One plan sub-issue listing every unit, as `ADR-004` read it.** Rejected.
  The units are issues anyway, since each pull request needs one to close
  under `branch-naming.md`. The list would restate them, and its "blocked by"
  prose would restate the dependencies the forge can hold natively.
- **The plan in the parent's body only, no sub-issues.** Rejected where the
  forge has sub-issues. Each unit then has no issue of its own for its branch
  to carry and its pull request to close. It remains the fallback for a
  forge without them.
- **A plan document in the repository.** Rejected before, by `ADR-004`, and
  for the same reason: three sources of truth for one plan.
